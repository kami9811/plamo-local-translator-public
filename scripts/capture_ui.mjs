import {chromium} from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const base=process.env.PLAMO_CAPTURE_URL;
if(!base||!['127.0.0.1','localhost'].includes(new URL(base).hostname))throw Error('Set PLAMO_CAPTURE_URL to an isolated loopback API.');
const output=path.resolve(process.env.PLAMO_CAPTURE_OUTPUT||path.join(root,'work/ui-capture'));
await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({channel:'chromium',headless:true,args:['--no-sandbox']});
let page;let initialSettings;
const evidence={viewport:{width:1440,height:900},checks:[],screenshots:[],font_usage:null,editor:null,mobile:null};
const views=[['テキスト翻訳','workspace'],['原稿ワークスペース','documents'],['用語と文脈','glossary'],['接続と設定','settings']];
const text='Our results suggest that the proposed method may improve accuracy by 12.5%. However, the difference was not statistically significant.';
try{
 const context=await browser.newContext({viewport:evidence.viewport,colorScheme:'light',reducedMotion:'reduce'});
 page=await context.newPage();await page.goto(new URL('app.html',base).href);
 await page.getByText('接続済み · PC内で処理',{exact:true}).waitFor();
 initialSettings=await page.evaluate(async()=>{const {token}=await(await fetch('/api/bootstrap')).json();return(await fetch('/api/settings',{headers:{Authorization:'Bearer '+token}})).json();});
 evidence.initial_theme=initialSettings.theme||'system';
 await page.locator('#direction').selectOption('en-ja');await page.locator('#model').selectOption('2b');
 await page.locator('#source').fill(text);await page.locator('#translate').click();
 await page.waitForFunction(()=>document.querySelector('#translation-status')?.textContent==='完了',null,{timeout:60000});
 for(const theme of ['light','dark']){
  await page.getByRole('button',{name:'接続と設定',exact:true}).click();
  await page.locator('#theme').selectOption(theme);await page.emulateMedia({colorScheme:theme,reducedMotion:'reduce'});
  await page.waitForFunction(t=>document.documentElement.dataset.theme===t,theme);
  for(const [name,slug]of views){
   await page.getByRole('button',{name,exact:true}).click();await page.evaluate(()=>document.fonts.ready);
   const actual=await page.evaluate(()=>({theme:document.documentElement.dataset.theme,scheme:getComputedStyle(document.documentElement).colorScheme,background:getComputedStyle(document.body).backgroundColor,title:document.querySelector('h1').textContent,overflow:document.documentElement.scrollWidth>innerWidth}));
   if(actual.theme!==theme||actual.scheme!==theme||actual.title!==name||actual.overflow)throw Error('Screenshot state mismatch: '+JSON.stringify(actual));
   if(actual.background!==(theme==='light'?'rgb(245, 246, 244)':'rgb(21, 27, 24)'))throw Error('Wrong background for '+theme);
   const issues=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
   evidence.checks.push({view:name,theme,background:actual.background,violations:issues.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))});
   if(issues.violations.length)throw Error('Accessibility findings in '+name+'/'+theme);
   if(slug==='workspace'){
    await page.mouse.move(1430,890);
    const file=`workspace-${theme}.png`;const buffer=await page.screenshot({path:path.join(output,file)});
    evidence.screenshots.push({file,theme,background:actual.background,sha256:createHash('sha256').update(buffer).digest('hex')});
   }
  }
 }
 await page.getByRole('button',{name:'テキスト翻訳',exact:true}).click();
 const cdp=await context.newCDPSession(page);await cdp.send('DOM.enable');await cdp.send('CSS.enable');
 const {root:doc}=await cdp.send('DOM.getDocument');const {nodeId}=await cdp.send('DOM.querySelector',{nodeId:doc.nodeId,selector:'#translation'});
 evidence.font_usage=await cdp.send('CSS.getPlatformFontsForNode',{nodeId});
 if(!evidence.font_usage.fonts.some(f=>f.isCustomFont&&f.familyName.startsWith('Noto Sans JP')))throw Error('Bundled Japanese font is not rendered');
 const measure=()=>page.locator('#source').evaluate(n=>({height:n.getBoundingClientRect().height,fontSize:getComputedStyle(n).fontSize,clientHeight:n.clientHeight,scrollHeight:n.scrollHeight}));
 const short=await measure();await page.locator('#source').fill(Array(40).fill('長い原稿を入力しても、入力欄は上限まで広がり、読みやすい文字サイズを保ちます。').join('\n'));const long=await measure();
 if(!(long.height>short.height&&long.height<=480&&short.fontSize==='18px'))throw Error('Editor resizing is incorrect');
 evidence.editor={short,long};await page.locator('#source').fill(text);
 await page.setViewportSize({width:390,height:844});
 evidence.mobile=[];
 for(const [name]of views){await page.getByRole('button',{name,exact:true}).click();const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);evidence.mobile.push({view:name,overflow});if(overflow)throw Error('Mobile overflow in '+name);}
 await fs.writeFile(path.join(output,'capture-evidence.json'),JSON.stringify(evidence,null,2)+'\n');
 console.log(JSON.stringify(evidence));
}finally{
 if(page&&initialSettings)await page.evaluate(async settings=>{const {token}=await(await fetch('/api/bootstrap')).json();await fetch('/api/settings',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify(settings)});},initialSettings).catch(()=>{});
 await browser.close();
}
