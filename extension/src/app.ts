import {api,BASE,download,el,isExtension,Job,labels,Options,pair,State,Task,wait} from './shared';
const $=<T extends HTMLElement=HTMLElement>(id:string)=>document.getElementById(id) as T;
const input=(id:string)=>$<HTMLInputElement>(id);
const select=(id:string)=>$<HTMLSelectElement>(id);
let state:State|undefined;let activeJob='';let renderedJob='';let translationId='';let initial=true;let refreshBusy=false;let jobBusy=false;
function notify(message:string,error=false){const n=$('notice');n.textContent=message;n.className='notice'+(error?' error':'');n.setAttribute('role',error?'alert':'status');n.hidden=false;}
function failure(error:unknown){notify(error instanceof Error?error.message:String(error),true);}
function action(id:string,fn:()=>Promise<unknown>|unknown){$(id).addEventListener('click',()=>Promise.resolve().then(fn).catch(failure));}
const views:Record<string,[string,string]>={translate:['テキスト翻訳','原文と訳文を並べて、PC内で翻訳します。'],documents:['原稿ワークスペース','段落ごとの下訳を確認し、原文付きのレビュー用ファイルに書き出します。'],glossary:['用語と文脈','専門用語と参考文脈を、プロジェクトごとに保存します。'],settings:['接続と設定','ローカルエンジンとの接続、表示、保存データを管理します。']};
function view(name:string){if(!$('notice').classList.contains('error'))$('notice').hidden=true;const current=views[name]||views.translate;$('page-title').textContent=current[0];$('page-description').textContent=current[1];document.title=current[0]+' — PLaMo Local';document.querySelectorAll<HTMLElement>('[id^="view-"]').forEach(n=>n.hidden=n.id!=='view-'+name);document.querySelectorAll<HTMLButtonElement>('nav [data-view]').forEach(n=>{if(n.dataset.view===name)n.setAttribute('aria-current','page');else n.removeAttribute('aria-current');});}
document.querySelectorAll<HTMLButtonElement>('[data-view]').forEach(n=>n.onclick=()=>view(n.dataset.view!));
function theme(value:string){if(value==='system')delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme=value;}
function dirty(){$('settings-saved').textContent='変更はまだ保存されていません。';}
function addTerm(source='',target=''){
 const row=el('tr');const a=el('input');a.value=source;a.maxLength=300;a.setAttribute('aria-label','原語');a.dataset.term='source';
 const b=el('input');b.value=target;b.maxLength=300;b.setAttribute('aria-label','訳語');b.dataset.term='target';
 const remove=el('button','削除');remove.setAttribute('aria-label',`用語 ${source||'新規'} を削除`);remove.onclick=()=>{row.remove();dirty();};
 for(const node of [a,b,remove]){const td=el('td');td.append(node);row.append(td);}a.oninput=b.oninput=dirty;$('glossary-rows').append(row);
}
function readOptions():Options{
 const [source,target]=select('direction').value.split('-') as ['en'|'ja','en'|'ja'];
 const glossary=Array.from($('glossary-rows').querySelectorAll('tr')).map(row=>({source:row.querySelector<HTMLInputElement>('[data-term=source]')!.value.trim(),target:row.querySelector<HTMLInputElement>('[data-term=target]')!.value.trim()})).filter(g=>g.source||g.target);
 return{model:select('model').value as Options['model'],source_lang:source,target_lang:target,form:select('form').value as Options['form'],domain:input('domain').value,context:$<HTMLTextAreaElement>('context').value,glossary,theme:select('theme').value as Options['theme']};
}
function applyOptions(opts:Options){select('model').value=opts.model;select('direction').value=opts.source_lang+'-'+opts.target_lang;select('form').value=opts.form;input('domain').value=opts.domain;$<HTMLTextAreaElement>('context').value=opts.context;$('glossary-rows').replaceChildren();for(const g of opts.glossary)addTerm(g.source,g.target);select('theme').value=opts.theme||select('theme').value||'system';theme(select('theme').value);$('settings-saved').textContent='';}
async function saveSettings(){const opts=readOptions();await api('/api/settings','POST',opts);theme(opts.theme||'system');$('settings-saved').textContent='保存しました。以降の翻訳に反映します。';}
async function refresh(){
 if(refreshBusy)return;refreshBusy=true;
 try{
  const next=await api<State>('/api/state');state=next;$('connection-state').textContent='接続済み · PC内で処理';$('connection-dot').classList.add('ok');
  const engine=next.engine;$('engine-state').textContent=`${engine.model?.toUpperCase()||'モデル'} · ${labels[engine.state]||engine.state}`;
  $('engine-detail').textContent=engine.error || `読み込み済み: ${engine.model?.toUpperCase()||'なし'}${engine.load_seconds===null?'':` · 読み込み ${engine.load_seconds.toFixed(2)}秒`}`;
  if(initial){applyOptions(next.settings);initial=false;$('notice').hidden=true;}
  const list=$('job-list');const signature=JSON.stringify(next.jobs);
  if(list.dataset.signature!==signature){list.dataset.signature=signature;list.replaceChildren();if(!next.jobs.length)list.append(el('p','保存した原稿はありません。','empty'));
   for(const job of next.jobs){const button=el('button');button.setAttribute('aria-current',String(activeJob===job.id));button.append(el('span',job.title),el('small',`${labels[job.status]||job.status} · ${job.completed}/${job.total}`));button.onclick=()=>{activeJob=job.id;renderedJob='';showJob().catch(failure);list.dataset.signature='';};list.append(button);}}
  const profiles=select('profile-select');const ps=JSON.stringify(next.profiles.map(p=>[p.id,p.name]));if(profiles.dataset.signature!==ps){profiles.dataset.signature=ps;const old=profiles.value;profiles.replaceChildren(new Option('選択してください',''));for(const p of next.profiles)profiles.add(new Option(p.name,p.id));profiles.value=old;}
  if(activeJob)await showJob();
 }catch(e){$('connection-state').textContent='未接続';$('connection-dot').classList.remove('ok');if(initial){view('settings');notify('ローカルエンジンを起動し、この画面に接続キーを登録してください。',true);}}
 finally{refreshBusy=false;}
}
async function showJob(){
 if(!activeJob||jobBusy)return;jobBusy=true;
 try{const job=await api<Job>(`/api/jobs/${activeJob}`);const signature=JSON.stringify(job);if(signature===renderedJob)return;renderedJob=signature;
 $('job-empty').hidden=true;$('job-detail').hidden=false;$('job-title').textContent=job.title;
 const done=job.segments.filter(s=>s.status==='done').length;$('job-status').textContent=`${labels[job.status]||job.status} · ${done}/${job.segments.length}`;
 $<HTMLProgressElement>('job-progress').max=job.segments.length||1;$<HTMLProgressElement>('job-progress').value=done;
 $<HTMLButtonElement>('pause-job').disabled=!['running','queued'].includes(job.status);$<HTMLButtonElement>('resume-job').disabled=['running','queued','done'].includes(job.status);$<HTMLButtonElement>('retry-job').disabled=!job.segments.some(s=>s.status==='error')||['running','queued'].includes(job.status);$<HTMLButtonElement>('delete-job').disabled=['running','queued'].includes(job.status);
 const processing=['running','queued'].includes(job.status);
 $('pause-job').hidden=!processing;$('resume-job').hidden=processing||job.status==='done';$('retry-job').hidden=!job.segments.some(s=>s.status==='error');
 const target=$('job-segments');target.replaceChildren();
 if(job.error)target.append(el('p',job.error,'warning'));
 for(const s of job.segments){if(s.skip)continue;const row=el('article',undefined,'pair');row.append(el('span',`${s.id} · ${labels[s.status]||s.status}`,'badge'));const grid=el('div',undefined,'pair-grid');for(const [title,text]of [['原文',s.source],['下訳',s.translation||'未翻訳']]){const col=el('div');col.append(el('h3',title),el('pre',text));grid.append(col);}row.append(grid);for(const w of s.warnings)row.append(el('p',w,'warning'));if(s.error)row.append(el('p',s.error,'warning'));target.append(row);}
 }finally{jobBusy=false;}
}
async function translate(){
 const text=$<HTMLTextAreaElement>('source').value.trim();if(!text)throw new Error('原文を入力してください。');
 fitSource();await saveSettings();$('notice').hidden=true;$<HTMLButtonElement>('translate').disabled=true;$<HTMLButtonElement>('cancel-translation').disabled=false;$('cancel-translation').hidden=false;$<HTMLButtonElement>('copy-translation').disabled=true;$('translation').textContent='';$('translation-warnings').hidden=true;$('translation-metrics').textContent='';
 try{let task=await api<Task>('/api/translations','POST',{text,options:readOptions()});translationId=task.id;
  for(;;){$('translation').textContent=task.translation;$('translation-status').textContent=labels[task.status]||task.status;
   if(['done','error','cancelled'].includes(task.status))break;await wait(120);task=await api<Task>(`/api/translations/${translationId}`);}
  if(task.status==='error')throw new Error(task.error||'翻訳に失敗しました。');
  if(task.status==='done'){$<HTMLButtonElement>('copy-translation').disabled=false;if(task.warnings.length){$('translation-warnings').textContent=task.warnings.join('\n');$('translation-warnings').hidden=false;}if(task.metrics)$('translation-metrics').textContent=task.metrics.cache_hit?'キャッシュから表示':`最初の応答 ${task.metrics.ttft_seconds.toFixed(2)}秒 · 完了 ${task.metrics.elapsed_seconds.toFixed(2)}秒`;}
 }finally{translationId='';$<HTMLButtonElement>('translate').disabled=false;$<HTMLButtonElement>('cancel-translation').disabled=true;$('cancel-translation').hidden=true;refresh();}
}
action('translate',translate);action('cancel-translation',async()=>{if(translationId)await api(`/api/translations/${translationId}/cancel`,'POST',{});});
action('copy-translation',async()=>{await navigator.clipboard.writeText($('translation').textContent||'');notify('訳文をコピーしました。');});
action('insert-sample',()=>{$<HTMLTextAreaElement>('source').value=select('direction').value==='en-ja'?'Our results suggest that the proposed method improves accuracy by 12.5%. However, the effect was not statistically significant.':'本研究の結果は、提案手法が精度を12.5%改善する可能性を示唆する。ただし、その効果は統計的に有意ではなかった。';$('char-count').textContent=$<HTMLTextAreaElement>('source').value.length+'文字';fitSource();});
function fitSource(){const source=$<HTMLTextAreaElement>('source');source.style.height='auto';source.style.height=Math.min(480,Math.max(180,source.scrollHeight))+'px';}
$<HTMLTextAreaElement>('source').oninput=()=>{fitSource();$('char-count').textContent=$<HTMLTextAreaElement>('source').value.length+'文字';};
action('load-model',async()=>{await saveSettings();await api('/api/models/load','POST',{model:select('model').value});notify('モデルを読み込んでいます。状態表示をご確認ください。');});
action('stop-engine',async()=>{await api('/api/models/stop','POST',{});notify('翻訳を中断し、モデルを停止します。');});
for(const id of ['model','direction','form','theme'])select(id).onchange=()=>saveSettings().catch(failure);
for(const id of ['domain','context'])$(id).oninput=dirty;
action('save-settings',saveSettings);action('add-term',()=>{if($('glossary-rows').children.length>=200)throw new Error('用語集は200件までです。');addTerm();dirty();});
function validateGlossary(value:unknown):{source:string;target:string}[]{if(!Array.isArray(value)||value.length>200||value.some(g=>!g||typeof g.source!=='string'||typeof g.target!=='string'||!g.source||!g.target||g.source.length>300||g.target.length>300))throw new Error('用語集のJSON形式を確認してください。');return value;}
$<HTMLInputElement>('glossary-file').onchange=async()=>{try{const f=input('glossary-file').files?.[0];if(!f)return;if(f.size>200000)throw new Error('用語集ファイルが大きすぎます。');const data=JSON.parse(await f.text());const terms=validateGlossary(Array.isArray(data)?data:data.glossary);$('glossary-rows').replaceChildren();for(const g of terms)addTerm(g.source,g.target);dirty();}catch(e){failure(e);}};
action('export-glossary',()=>download('plamo-glossary.json',JSON.stringify({schema_version:'1.0',glossary:readOptions().glossary},null,2),'application/json'));
action('save-profile',async()=>{await saveSettings();await api('/api/profiles','POST',{name:input('profile-name').value,options:readOptions()});notify('プロジェクト設定を保存しました。');await refresh();});
action('load-profile',async()=>{const p=state?.profiles.find(p=>p.id===select('profile-select').value);if(!p)throw new Error('設定を選んでください。');applyOptions({...p.options,theme:select('theme').value as Options['theme']});await saveSettings();notify('プロジェクト設定を読み込みました。');});
action('delete-profile',async()=>{const id=select('profile-select').value;if(!id)throw new Error('設定を選んでください。');if(confirm('このプロジェクト設定を削除しますか？')){await api(`/api/profiles/${id}`,'DELETE');await refresh();}});
$<HTMLInputElement>('doc-file').onchange=async()=>{try{const f=input('doc-file').files?.[0];if(!f)return;if(f.size>4000000)throw new Error('ファイルは4MBまでです。');const fmt=f.name.split('.').pop()?.toLowerCase();if(!['txt','md','tex'].includes(fmt||''))throw new Error('txt・md・texファイルを選んでください。');const text=new TextDecoder('utf-8',{fatal:true}).decode(await f.arrayBuffer());if(text.length>500000)throw new Error('原稿は500,000文字までです。');$<HTMLTextAreaElement>('doc-source').value=text;input('doc-title').value=f.name;select('doc-format').value=fmt!;}catch(e){failure(e);}};
action('create-job',async()=>{const button=$<HTMLButtonElement>('create-job');button.disabled=true;try{await saveSettings();const job=await api<Job>('/api/jobs','POST',{text:$<HTMLTextAreaElement>('doc-source').value,title:input('doc-title').value||'名称未設定',format:select('doc-format').value,options:readOptions()});activeJob=job.id;renderedJob='';$<HTMLDetailsElement>('new-document').open=false;await refresh();}finally{button.disabled=false;}});
for(const [id,cmd]of [['pause-job','cancel'],['resume-job','resume'],['retry-job','retry']])action(id,async()=>{if(activeJob){await api(`/api/jobs/${activeJob}/${cmd}`,'POST',{});await refresh();}});
action('delete-job',async()=>{if(activeJob&&confirm('この原稿と対訳をPC内の保存データから削除しますか？')){await api(`/api/jobs/${activeJob}`,'DELETE');activeJob='';renderedJob='';$('job-detail').hidden=true;$('job-empty').hidden=false;await refresh();}});
document.querySelectorAll<HTMLButtonElement>('[data-export]').forEach(button=>button.onclick=async()=>{try{if(!activeJob)return;const kind=button.dataset.export!;const r=await fetch(BASE+`/api/jobs/${activeJob}/export?format=${kind}`,{redirect:'error',credentials:'omit',referrerPolicy:'no-referrer',headers:{Authorization:'Bearer '+await (await import('./shared')).readToken()}});if(!r.ok)throw new Error('出力に失敗しました。');const text=await r.text();if(kind==='json'){const bundle=JSON.parse(text);if(!bundle.source_text||!Array.isArray(bundle.segments))throw new Error('出力内容が不足しています。');}const job=await api<Job>(`/api/jobs/${activeJob}`);const name=job.title.replace(/[^\p{L}\p{N}._-]+/gu,'_').slice(0,80)||'paper';await download(`${name}${kind==='translated'?'.translated.'+job.format:'.review.'+kind}`,text,kind==='json'?'application/json':'text/plain;charset=utf-8');notify(job.status==='done'?'出力しました。原文と下訳を照合してレビューしてください。':'未完了の段落を含む原稿を出力しました。処理状態をご確認ください。');}catch(e){failure(e);}});
action('pair',async()=>{await pair(input('connection-key').value);input('connection-key').value='';initial=true;await refresh();notify('接続しました。');});
action('refresh',async()=>{initial=true;await refresh();});
action('clear-cache',async()=>{if(confirm('翻訳キャッシュを削除しますか？ 原稿と用語集は残ります。')){await api('/api/cache','DELETE');notify('翻訳キャッシュを削除しました。');}});
action('clear-data',async()=>{if(confirm('保存した原稿・対訳・用語集・設定・キャッシュをすべて削除します。この操作は取り消せません。')){await api('/api/data','DELETE');activeJob='';initial=true;renderedJob='';$('job-detail').hidden=true;$('job-empty').hidden=false;await refresh();notify('保存データを削除しました。モデルと接続キーは保持されています。');}});
view(new URL(location.href).searchParams.get('view')||'translate');refresh();setInterval(refresh,1200);

if(isExtension){
 $('shortcut-settings').hidden=false;
 chrome.commands.getAll().then(commands=>{$('shortcut-state').textContent=commands.filter(c=>c.name!=='_execute_action').map(c=>`${c.name==='translate-selection'?'選択文':'ページ'}: ${c.shortcut||'未設定'}`).join(' ／ ');});
 action('open-shortcuts',()=>chrome.tabs.create({url:'chrome://extensions/shortcuts'}));
}
