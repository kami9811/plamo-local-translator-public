import {api,Options,Task,wait} from './shared';
chrome.storage.local.setAccessLevel({accessLevel:'TRUSTED_CONTEXTS'}).catch(()=>{});
chrome.runtime.onInstalled.addListener(()=>{
 chrome.contextMenus.removeAll(()=>chrome.contextMenus.create({id:'plamo-translate',title:'PLaMoで選択文を翻訳',contexts:['selection']}));
});
async function onTab(action:string,text?:string,explicitTab?:chrome.tabs.Tab){
 const tab=explicitTab || (await chrome.tabs.query({active:true,currentWindow:true}))[0];
 if(!tab?.id || !/^https?:/.test(tab.url||''))throw new Error('通常のWebページで実行してください。');
 await chrome.scripting.executeScript({target:{tabId:tab.id},files:['content.js']});
 await chrome.tabs.sendMessage(tab.id,{plamo:true,action,text});
}
chrome.contextMenus.onClicked.addListener((info,tab)=>{if(info.menuItemId==='plamo-translate')onTab('selection',info.selectionText,tab).catch(console.warn);});
chrome.commands.onCommand.addListener(command=>onTab(command==='translate-page'?'page':'selection').catch(console.warn));
chrome.runtime.onMessage.addListener((message,sender,reply)=>{
 if(sender.id!==chrome.runtime.id || !sender.url?.startsWith(chrome.runtime.getURL('')))return;
 if(message?.kind==='tab-action'){onTab(message.action).then(()=>reply({ok:true}),e=>reply({error:String(e.message)}));return true;}
});
chrome.runtime.onConnect.addListener(port=>{
 if(port.name!=='plamo-translation' || port.sender?.id!==chrome.runtime.id)return;
 let ident:string|undefined;let cancelled=false;
 const stop=()=>{cancelled=true;if(ident)api(`/api/translations/${ident}/cancel`,'POST',{}).catch(()=>{});};
 port.onDisconnect.addListener(stop);
 port.onMessage.addListener(async message=>{
  if(message.kind==='cancel'){stop();return;}
  if(message.kind!=='translate' || typeof message.text!=='string' || message.text.length>8000)return;
  try{
   const opts=await api<Options>('/api/settings');
   if(typeof message.context==='string')opts.context=[opts.context,message.context.slice(0,1600)].filter(Boolean).join('\n');
   if(cancelled)return;
   let task=await api<Task>('/api/translations','POST',{text:message.text,options:opts});ident=task.id;
   if(cancelled){stop();return;}
   for(;;){port.postMessage({...task,theme:opts.theme||'system'});if(['done','error','cancelled'].includes(task.status))break;await wait(120);if(cancelled)return;task=await api<Task>(`/api/translations/${ident}`);}
  }catch(e){if(!cancelled)try{port.postMessage({status:'error',error:e instanceof Error?e.message:String(e)});}catch{stop();}}
 });
});
