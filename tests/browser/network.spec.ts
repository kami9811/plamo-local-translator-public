import { test, expect, chromium } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';

test('extension confines app fetches, rejects redirects, and renders untrusted text as text',async()=>{
  const root=process.cwd();const requests:string[]=[];let redirect=false;
  const opts={model:'2b',source_lang:'en',target_lang:'ja',form:'plain',domain:'',context:'',glossary:[],theme:'light'};
  const state={engine:{state:'ready',model:'2b',error:'',load_seconds:0,models:[{id:'2b',available:true,bytes:0},{id:'8b',available:true,bytes:0}]},settings:opts,jobs:[],profiles:[]};
  const hostile='<img src="https://example.invalid/leak" onerror="alert(1)">';
  const context=await chromium.launchPersistentContext(path.join(root,'work/network-browser-profile'),{
    executablePath:process.env.PLAMO_TEST_CHROME,headless:true,
    args:[`--disable-extensions-except=${root}/dist`,`--load-extension=${root}/dist`,'--disable-background-networking','--no-sandbox'],
  });
  try {
    context.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
    await context.route('http://127.0.0.1:8765/api/**',async route=>{
      const url=new URL(route.request().url());
      if(redirect&&url.pathname==='/api/state'){
        await route.fulfill({status:302,headers:{Location:'https://example.invalid/redirect','Access-Control-Allow-Origin':'*'}});return;
      }
      let value:unknown=state;
      if(url.pathname==='/api/translations')value={id:'security-fixture',status:'queued',translation:'',warnings:[]};
      if(url.pathname==='/api/translations/security-fixture')value={id:'security-fixture',status:'done',translation:hostile,warnings:[],metrics:{elapsed_seconds:0,ttft_seconds:0,cache_hit:false}};
      await route.fulfill({status:200,contentType:'application/json',headers:{'Access-Control-Allow-Origin':'*'},body:JSON.stringify(value)});
    });
    let worker=context.serviceWorkers()[0];if(!worker)worker=await context.waitForEvent('serviceworker');
    const id=worker.url().split('/')[2];const page=await context.newPage();
    await page.goto(`chrome-extension://${id}/app.html?view=settings`);
    await page.locator('#connection-key').fill('synthetic-fixture-key');await page.locator('#pair').click();
    await expect(page.locator('#connection-state')).toContainText('接続済み');
    await page.getByRole('button',{name:'テキスト翻訳',exact:true}).click();
    await page.locator('#source').fill('Synthetic document for network checks.');await page.locator('#translate').click();
    await expect(page.locator('#translation-status')).toHaveText('完了');
    await expect(page.locator('#translation')).toHaveText(hostile);await expect(page.locator('#translation img')).toHaveCount(0);
    const violation=await page.evaluate(async()=>{
      const seen:string[]=[];const capture=(event:SecurityPolicyViolationEvent)=>seen.push(event.effectiveDirective);
      document.addEventListener('securitypolicyviolation',capture);
      let rejected=false;try{await fetch('https://example.invalid/blocked',{method:'POST',body:'synthetic-fixture-only'});}catch{rejected=true;}
      await new Promise(r=>setTimeout(r,50));document.removeEventListener('securitypolicyviolation',capture);
      return {rejected,seen};
    });
    expect(violation.rejected).toBeTruthy();expect(violation.seen).toContain('connect-src');
    redirect=true;await page.getByRole('button',{name:'接続と設定',exact:true}).click();await page.locator('#refresh').click();
    await page.waitForTimeout(200);
    expect(requests.some(url=>url.includes('/redirect'))).toBeFalsy();
    expect(requests.filter(url=>!url.startsWith('http://127.0.0.1:8765/'))).toEqual([]);
    fs.writeFileSync('work/network-browser-evidence.json',JSON.stringify({
      real_models:false,api:'intercepted fixture, no user API started',
      translation_fixture_rendered_as_text:true,external_fetch_blocked_by_csp:true,
      external_redirect_not_followed:true,app_request_origins:[...new Set(requests.map(x=>new URL(x).origin))],
      whole_browser_packet_capture:false,
    },null,2));
  } finally {await context.close();}
});
