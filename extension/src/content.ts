import tokens from '../public/tokens.css';
import {el,labels,Task} from './shared';
// A user action may inject this bundle repeatedly; listeners are installed once per page.
const key='__plamoLocalInstalled';
const page=window as unknown as Record<string,unknown>;
if(!page[key]){
 page[key]=true;
 // Load the bundled font from bytes; viewed-page font-src policies cannot redirect this request.
 const fontReady=fetch(chrome.runtime.getURL('fonts/NotoSansJP-VF.woff2')).then(r=>{if(!r.ok)throw new Error('font');return r.arrayBuffer();}).then(async bytes=>{
  const face=new FontFace('PLaMo Sans',bytes,{weight:'100 900',style:'normal'});await face.load();document.fonts.add(face);
 }).catch(()=>{});
 void fontReady;
 let restoreFocus:HTMLElement|undefined;let host:HTMLDivElement|undefined;let activePort:chrome.runtime.Port|undefined;let pageRunning=false;let pageCancelled=false;
 const originals=new Map<Text,{source:string;translated:string}>();
 const styles=`${tokens.replaceAll(':root',':host')}
:host{all:initial;font:400 15px/1.75 var(--font-sans);font-synthesis:none;color:var(--text)}*{box-sizing:border-box}.panel{background:var(--surface);border:1px solid var(--line);border-radius:16px;box-shadow:0 12px 40px #0002;padding:20px;width:min(460px,calc(100vw - 24px));max-height:70vh;overflow:auto}.top{display:flex;align-items:center;justify-content:space-between;gap:12px}.title{font-size:14px;font-weight:600;color:var(--text);letter-spacing:0}button{font:500 13px/1.6 var(--font-sans);border:1px solid var(--line);border-radius:8px;padding:8px 12px;min-height:40px;background:transparent;color:inherit;cursor:pointer}button:focus-visible{outline:3px solid var(--primary);outline-offset:3px}button:disabled{opacity:.5;cursor:default}.output{white-space:pre-wrap;overflow-wrap:anywhere;margin:16px 0;user-select:text;font:400 15px/1.8 var(--font-sans)}.status,.attribution{font-size:11px;line-height:1.6;color:var(--muted)}.status{margin-top:10px}.attribution{margin-top:16px;padding-top:12px;border-top:1px solid var(--line)}.actions{display:flex;gap:8px;flex-wrap:wrap}.error{color:var(--error)}@media(prefers-reduced-motion:no-preference){.panel{animation:in .15s ease-out}@keyframes in{from{opacity:0;transform:translateY(5px)}}}`;
 function close(){activePort?.disconnect();activePort=undefined;pageCancelled=true;host?.remove();host=undefined;restoreFocus?.focus({preventScroll:true});}
 function panel(title:string){
  restoreFocus=document.activeElement instanceof HTMLElement?document.activeElement:undefined;host?.remove();host=el('div');host.setAttribute('data-plamo-root','');Object.assign(host.style,{position:'fixed',zIndex:'2147483647',right:'16px',bottom:'16px'});
  const root=host.attachShadow({mode:'open'});const sheet=new CSSStyleSheet();sheet.replaceSync(styles);root.adoptedStyleSheets=[sheet];
  const box=el('section',undefined,'panel');box.setAttribute('role','region');box.setAttribute('aria-label',title);
  const top=el('div',undefined,'top');top.append(el('span',title,'title'));const x=el('button','閉じる');x.onclick=close;top.append(x);
  const status=el('div','準備中…','status');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  const output=el('div','','output');const actions=el('div',undefined,'actions');box.append(top,status,output,actions,el('div','Built with PLaMo · 非公式ツール','attribution'));root.append(box);document.documentElement.append(host);
  x.focus({preventScroll:true});box.addEventListener('keydown',e=>{if(e.key==='Escape')close();});return{box,status,output,actions};
 }
 function translate(text:string,onUpdate:(t:Task)=>void){
  return new Promise<Task>((resolve,reject)=>{const port=chrome.runtime.connect({name:'plamo-translation'});activePort=port;let finished=false;
   port.onMessage.addListener((task:Task)=>{if(host&&task.theme){if(task.theme==='system')delete host.dataset.theme;else host.dataset.theme=task.theme;}onUpdate(task);if(['done','error','cancelled'].includes(task.status)){finished=true;port.disconnect();if(activePort===port)activePort=undefined;task.status==='done'?resolve(task):reject(new Error(task.error||'翻訳を中断しました。'));}});
   port.onDisconnect.addListener(()=>{if(!finished)reject(new Error('翻訳を中断しました。'));});
   port.postMessage({kind:'translate',text,context:document.title});
  });
 }
 async function selection(text?:string){
  close();const source=(text||window.getSelection()?.toString()||'').trim();const ui=panel('PLaMo Local · 選択文');
  if(!source){ui.status.textContent='翻訳する文章を選択してください。';return;}
  const run=async()=>{
   ui.output.textContent='';ui.status.className='status';retry.disabled=true;copy.disabled=true;
   try{const task=await translate(source,t=>{ui.output.textContent=t.translation||'';ui.status.textContent=labels[t.status]||t.status;});ui.status.textContent=task.warnings.length?task.warnings.join('\n'):`完了${task.metrics?.cache_hit?' · キャッシュ':''}`;copy.disabled=false;}
   catch(e){ui.status.textContent=e instanceof Error?e.message:String(e);ui.status.classList.add('error');}
   finally{retry.disabled=false;}
  };
  const copy=el('button','訳文をコピー');copy.disabled=true;copy.onclick=async()=>{try{const text=ui.output.textContent||'';if(navigator.clipboard)await navigator.clipboard.writeText(text);else{const area=el('textarea');area.value=text;area.setAttribute('aria-label','コピー用の一時領域');Object.assign(area.style,{position:'fixed',left:'-10000px'});document.documentElement.append(area);area.select();const copied=document.execCommand('copy');area.remove();copy.focus();if(!copied)throw new Error('コピー失敗');}ui.status.textContent='コピーしました。';}catch{ui.status.textContent='コピーできませんでした。訳文を選択してコピーしてください。';}};
  const cancel=el('button','キャンセル');cancel.onclick=()=>activePort?.postMessage({kind:'cancel'});
  const retry=el('button','再試行');retry.onclick=run;ui.actions.append(copy,cancel,retry);await run();
 }
 function restore(){
  pageCancelled=true;activePort?.disconnect();
  let restored=0;for(const[node,value]of originals){if(node.isConnected && node.data===value.translated){node.data=value.source;restored++;}}
  originals.clear();const ui=panel('PLaMo Local · ページ翻訳');ui.status.textContent=`原文に戻しました（${restored}箇所）。`;return restored;
 }
 async function wholePage(){
  if(pageRunning){pageCancelled=true;activePort?.disconnect();return;}
  if(originals.size){restore();return;}
  close();pageCancelled=false;pageRunning=true;const ui=panel('PLaMo Local · ページ翻訳');
  const back=el('button','原文へ戻す');back.onclick=restore;
  const cancel=el('button','中断');cancel.onclick=()=>{pageCancelled=true;activePort?.disconnect();};ui.actions.append(cancel,back);
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,{acceptNode(node){
   const n=node as Text;const parent=n.parentElement;
   if(!parent || parent.closest('script,style,noscript,code,pre,textarea,input,select,option,button,svg,math,[contenteditable], [role="textbox"], [translate="no"], [data-plamo-root], [hidden], [aria-hidden="true"]') || !n.data.trim() || n.data.trim().length<2)return NodeFilter.FILTER_REJECT;
   if(!parent.getClientRects().length)return NodeFilter.FILTER_REJECT;
   return NodeFilter.FILTER_ACCEPT;
  }});
  const nodes:Text[]=[];let n:Node|null;while((n=walker.nextNode()))nodes.push(n as Text);
  let completed=0;let errors=0;
  try{for(const node of nodes){if(pageCancelled)break;if(!node.isConnected)continue;const source=node.data;if(source.length>8000){errors++;continue;}
    ui.status.textContent=`${completed}/${nodes.length}箇所を翻訳中`;
    try{const task=await translate(source,()=>{});if(pageCancelled)break;if(node.isConnected && node.data===source){const prefix=source.match(/^\s*/)?.[0]||'';const suffix=source.match(/\s*$/)?.[0]||'';const translated=prefix+task.translation.trim()+suffix;originals.set(node,{source,translated});node.data=translated;}completed++;}
    catch{errors++;if(pageCancelled)break;}
   }
   ui.status.textContent=`${pageCancelled?'中断':'完了'} · ${completed}/${nodes.length}箇所${errors?` · 未翻訳 ${errors}箇所`:''}`;
  }finally{pageRunning=false;}
 }
 chrome.runtime.onMessage.addListener((message,sender)=>{if(!message?.plamo || sender.id!==chrome.runtime.id)return;if(message.action==='selection')selection(message.text);if(message.action==='page')wholePage();if(message.action==='restore')restore();});
}
