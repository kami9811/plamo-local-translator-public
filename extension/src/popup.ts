import {api,isExtension,Options,State} from './shared';
const $=(id:string)=>document.getElementById(id)!;
let settings:Options|undefined;
function error(e:unknown){$('popup-error').textContent=e instanceof Error?e.message:String(e);$('popup-error').hidden=false;}
async function init(){try{const state=await api<State>('/api/state');settings=state.settings;(document.getElementById('popup-direction') as HTMLSelectElement).value=settings.source_lang+'-'+settings.target_lang;$('popup-status').textContent=`${settings.model.toUpperCase()} · PC内で処理`;}catch{$('popup-status').textContent='未接続 · 接続設定を開いてください。';}}
$('popup-direction').onchange=async()=>{try{if(!settings)throw new Error('先に接続キーを設定してください。');const[source,target]=(document.getElementById('popup-direction')as HTMLSelectElement).value.split('-')as['en'|'ja','en'|'ja'];settings.source_lang=source;settings.target_lang=target;await api('/api/settings','POST',settings);}catch(e){error(e);}};
for(const[id,action]of[['popup-selection','selection'],['popup-page','page']])$(id).onclick=async()=>{try{const result=await chrome.runtime.sendMessage({kind:'tab-action',action});if(result?.error)throw new Error(result.error);window.close();}catch(e){error(e);}};
$('popup-open').onclick=()=>chrome.tabs.create({url:chrome.runtime.getURL('app.html')+(settings?'':'?view=settings')});init();

chrome.commands.getAll().then(commands=>{const missing=commands.filter(c=>c.name!=='_execute_action'&&!c.shortcut);if(missing.length){$('popup-shortcuts').textContent='ショートカットが未設定です。Chromeの設定で割り当ててください。';$('popup-shortcut-settings').hidden=false;}});
$('popup-shortcut-settings').onclick=()=>chrome.tabs.create({url:'chrome://extensions/shortcuts'});
