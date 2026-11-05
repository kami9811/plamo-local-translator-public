"""Single GPU model lifecycle and streamed, context-bounded PFML3 inference."""
from __future__ import annotations
from pathlib import Path
import secrets
import hashlib, json, os, subprocess, threading, time, urllib.request

class Cancelled(Exception): pass

def options(raw: dict) -> dict:
    if not isinstance(raw,dict):raise ValueError('設定の形式が正しくありません。')
    model=raw.get('model','2b');source=raw.get('source_lang','en');target=raw.get('target_lang','ja')
    if model not in {'2b','8b'} or source not in {'en','ja'} or target not in {'en','ja'} or source==target:raise ValueError('モデルと翻訳方向を確認してください。')
    form=raw.get('form','plain')
    if form not in {'plain','polite'}:raise ValueError('文体を確認してください。')
    glossary=raw.get('glossary',[])
    if not isinstance(glossary,list) or len(glossary)>200:raise ValueError('用語集は200件までです。')
    for g in glossary:
        if not isinstance(g,dict) or any(not isinstance(g.get(k),str) or not g[k].strip() or len(g[k])>300 for k in ['source','target']):raise ValueError('用語集には原語と訳語を指定してください。')
    context=raw.get('context','');domain=raw.get('domain','')
    if not isinstance(context,str) or len(context)>10000 or not isinstance(domain,str) or len(domain)>500:raise ValueError('参考文脈が長すぎます。')
    return {'model':model,'source_lang':source,'target_lang':target,'form':form,'domain':domain,'context':context,'glossary':[{'source':g['source'],'target':g['target']} for g in glossary]}

def clean(value):return str(value).replace('<|plamo:','< |plamo:')
def prompt_for(text, opts, history=()):
    p='<|plamo:tag|>dataset<|plamo:msg|>translation'
    context='\n'.join(x for x in [opts['domain'],opts['context']] if x)
    if context:p+='<|plamo:tag|>context<|plamo:msg|>'+clean(context)
    for src,tgt in list(history)[-2:]:
        p+='<|plamo:tag|>input<|plamo:key|>lang<|plamo:val|>'+opts['source_lang']+'<|plamo:msg|>'+clean(src)
        p+='<|plamo:tag|>output<|plamo:key|>lang<|plamo:val|>'+opts['target_lang']+'<|plamo:msg|>'+clean(tgt)
    if opts['glossary']:
        p+='<|plamo:tag|>glossary'+''.join('<|plamo:index|>'+clean(g['source'])+'<|plamo:item|>'+clean(g['target']) for g in opts['glossary'])
    p+='<|plamo:tag|>input<|plamo:key|>lang<|plamo:val|>'+opts['source_lang']+'<|plamo:msg|>'+clean(text)
    p+='<|plamo:tag|>output<|plamo:key|>lang<|plamo:val|>'+opts['target_lang']
    if opts['target_lang']=='ja':p+='<|plamo:key|>form<|plamo:val|>'+opts['form']
    return p+'<|plamo:msg|>'

class Engine:
    def __init__(self, root: Path, data: Path):
        self.root=root;self.data=data;self.manifest=json.loads((root/'runtime-manifest.json').read_text())
        self.lock=threading.RLock();self.process=None;self.loaded=None;self.state='stopped';self.error='';self.load_seconds=None;self.port=int(os.environ.get('PLAMO_INFERENCE_PORT','8766'))
        self.active_cancel=None;self.api_key=secrets.token_urlsafe(32)
    def status(self):
        return {'state':self.state,'model':self.loaded,'error':self.error,'load_seconds':self.load_seconds,
                'models':[{ 'id':k,'file':v['file'],'bytes':v['bytes'],'available':(self.root/'.runtime/models'/v['file']).is_file()} for k,v in self.manifest['models'].items()]}
    def provenance(self,model):return {'id':model,**self.manifest['models'][model],'runtime':self.manifest['llama_tag'],'context_tokens':16384}
    def _request(self,path,payload=None,timeout=15):
        body=json.dumps(payload).encode() if payload is not None else None
        return urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{self.port}'+path,data=body,headers={'Content-Type':'application/json','Authorization':'Bearer '+self.api_key}),timeout=timeout)
    def _stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
        self.process=None;self.loaded=None;self.state='stopped'
    def stop(self):
        if self.active_cancel:self.active_cancel.set()
        with self.lock:self._stop()
    def load(self,model):
        if model not in self.manifest['models']:raise ValueError('モデルが不明です。')
        with self.lock:self._ensure(model)
    def _ensure(self,model):
        if self.loaded==model and self.process and self.process.poll() is None:return
        self._stop();self.state='loading';self.error='';started=time.perf_counter()
        try:
            binary=self.root/'.runtime/llama-build/bin/llama-server'
            if not binary.is_file():binary=next((self.root/'.runtime/llama').rglob('llama-server'),None)
            if not binary:raise ValueError('llama-serverがありません。セットアップを実行してください。')
            weights=self.root/'.runtime/models'/self.manifest['models'][model]['file']
            if not weights.is_file():raise ValueError('モデルがありません。セットアップを実行してください。')
            env=os.environ.copy();libdirs={str(x.parent) for x in (self.root/'.runtime/llama').rglob('*.so*')};libdirs.add('/usr/lib/wsl/lib');libdirs.add(str(self.root/'.runtime/llama-build/bin'));libdirs.add('/usr/local/cuda-12.6/lib64')
            env['LD_LIBRARY_PATH']=':'.join(sorted(libdirs))+':'+env.get('LD_LIBRARY_PATH','')
            log=(self.data/'llama.log').open('ab')
            self.process=subprocess.Popen([str(binary),'-m',str(weights),'-c','16384','-ngl','99','-t','12','--host','127.0.0.1','--port',str(self.port),'--parallel','1','--alias','plamo-local','--api-key',self.api_key,'--no-webui'],stdout=log,stderr=log,env=env)
            log.close()
            for _ in range(240):
                if self.process.poll() is not None:raise RuntimeError('推論エンジンが終了しました。.data/llama.logを確認してください。')
                try:
                    with self._request('/health',timeout=1) as r:
                        if r.status==200:
                            self.loaded=model;self.state='ready';self.load_seconds=round(time.perf_counter()-started,4);return
                except Exception:pass
                time.sleep(.5)
            raise TimeoutError('モデルの読み込みがタイムアウトしました。')
        except Exception as e:self._stop();self.state='error';self.error=str(e);raise
    def translate(self,text,opts,cancel,on_chunk=lambda _:None,history=()):
        with self.lock:
            if cancel.is_set():raise Cancelled()
            self._ensure(opts['model'])
            if cancel.is_set():raise Cancelled()
            self.active_cancel=cancel
            prompt=prompt_for(text,opts,history)
            with self._request('/tokenize',{'content':prompt,'add_special':True}) as r:count=len(json.load(r)['tokens'])
            limit=min(4096,16384-count-64)
            if limit<512:raise ValueError('文脈・用語集・原稿が入力上限に近すぎます。短くしてください。')
            payload={'prompt':prompt,'n_predict':limit,'temperature':0,'stream':True,'stop':['<|plamo:tag|>','<|plamo:bos|>'],'cache_prompt':True}
            result='';started=time.perf_counter();ttft=None;timings={};truncated=False
            try:
                with self._request('/completion',payload,timeout=180) as response:
                    for line in response:
                        if cancel.is_set():raise Cancelled()
                        if not line.startswith(b'data: '):continue
                        raw=line[6:].strip()
                        if raw==b'[DONE]':break
                        data=json.loads(raw);chunk=data.get('content','')
                        if chunk:
                            if ttft is None:ttft=time.perf_counter()-started
                            result+=chunk;on_chunk(result)
                        if data.get('stop'):
                            timings=data.get('timings',{});truncated=data.get('stopped_limit',False)
                if cancel.is_set():raise Cancelled()
                return result.strip(),{'ttft_seconds':round(ttft or 0,4),'elapsed_seconds':round(time.perf_counter()-started,4),'input_tokens':count,'timings':timings,'truncated':truncated,'cache_hit':False}
            finally:self.active_cancel=None
