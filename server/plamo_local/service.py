"""Threaded local service. No cloud calls, no arbitrary URL proxy."""
from __future__ import annotations
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
import signal
import atexit, copy, hashlib, hmac, json, mimetypes, os, re, secrets, threading, time, uuid
from .engine import Engine,Cancelled,options
from .documents import protect,segment,check_numbers,export_bundle,export_markdown
from .store import Store

API_PORT=int(os.environ.get('PLAMO_API_PORT','8765'))
LOCAL_HOSTS={f'127.0.0.1:{API_PORT}',f'localhost:{API_PORT}'}
LOCAL_ORIGINS={f'http://127.0.0.1:{API_PORT}',f'http://localhost:{API_PORT}'}

class App:
    def __init__(self,root,data):
        data.mkdir(parents=True,exist_ok=True,mode=0o700);data.chmod(0o700)
        self.root=root;self.data=data;self.store=Store(data);self.engine=Engine(root,data);self.tasks={};self.cancels={};self.runners={};self.guard=threading.RLock()
        tokenfile=data/'token'
        if not tokenfile.exists():tokenfile.write_text(secrets.token_urlsafe(32))
        tokenfile.chmod(0o600)
        self.token=tokenfile.read_text().strip()
        for job in self.store.list('job'):
            if job['status'] in {'running','queued'}:
                job['status']='paused'
                for s in job['segments']:
                    if s['status']=='running':s['status']='pending'
                self.store.put('job',job['id'],job)
    def settings(self):return self.store.get('config','settings') or {**options({}),'theme':'system'}
    def translate(self,text,opts,cancel,on_chunk=lambda _:None,history=()):
        protected=protect(text)
        key=hashlib.sha256(json.dumps({'text':text,'options':opts,'history':list(history)[-2:],'model':self.engine.provenance(opts['model']),'protect_version':1},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        cached=self.store.cache_get(key)
        if cached:
            if cancel.is_set():raise Cancelled()
            cached['metrics']={**cached['metrics'],'cache_hit':True,'ttft_seconds':0,'elapsed_seconds':0};on_chunk(cached['translation']);return cached
        def chunk(out):
            # Only final output is restored and validated. Partial output is visibly a draft.
            on_chunk(protected.restore(out)[0])
        output,metrics=self.engine.translate(protected.text,opts,cancel,chunk,history)
        translation,warnings=protected.restore(output)
        warnings+=check_numbers(text,translation)
        if metrics['truncated']:warnings.append('出力が長さの上限に達しました。文章を分割して再実行してください。')
        result={'translation':translation,'warnings':warnings,'metrics':metrics,'model':self.engine.provenance(opts['model'])}
        if not warnings:self.store.cache_put(key,result)
        return result
    def start_translation(self,text,opts):
        ident=uuid.uuid4().hex;cancel=threading.Event();self.cancels[ident]=cancel
        task={'id':ident,'status':'queued','translation':'','warnings':[]};self.tasks[ident]=task
        def run():
            task['status']='running'
            try:
                result=self.translate(text,opts,cancel,lambda value:task.update(translation=value))
                task.update(result,status='done')
            except Cancelled:task['status']='cancelled'
            except Exception as e:task.update(status='error',error=str(e))
            finally:
                self.cancels.pop(ident,None)
                # Bound transient memory. Persistent document jobs are managed separately.
                done=[k for k,v in self.tasks.items() if v['status'] in {'done','error','cancelled'}]
                for old in done[:-100]:self.tasks.pop(old,None)
        threading.Thread(target=run,daemon=True).start();return task
    def start_job(self,ident,retry=False):
        with self.guard:
            if self.runners.get(ident) and self.runners[ident].is_alive():raise ValueError('この原稿は処理中です。')
            job=self.store.get('job',ident)
            if not job:raise KeyError('原稿が見つかりません。')
            if retry:
                for s in job['segments']:
                    if s['status']=='error':s['status']='pending';s.pop('error',None)
            cancel=threading.Event();self.cancels[ident]=cancel;job['status']='queued';self.store.put('job',ident,job)
            def run():
                try:
                    job['status']='running';self.store.put('job',ident,job);history=[]
                    for s in job['segments']:
                        if cancel.is_set():raise Cancelled()
                        if s['status']=='done':
                            if not s['skip']:history.append((s['source'],s['translation']))
                            continue
                        if s['status']=='error':continue
                        if s['skip']:s.update(translation=s['source'],status='done',warnings=[]);self.store.put('job',ident,job);continue
                        s['status']='running';self.store.put('job',ident,job)
                        try:
                            result=self.translate(s['source'],job['options'],cancel,history=history[-2:])
                            s.update({k:v for k,v in result.items() if k!='model'},status='done');history.append((s['source'],s['translation']))
                        except Cancelled:s['status']='pending';raise
                        except Exception as e:
                            if cancel.is_set():s['status']='pending';raise Cancelled()
                            s.update(status='error',error=str(e))
                        self.store.put('job',ident,job)
                    job['status']='error' if any(s['status']=='error' for s in job['segments']) else 'done'
                except Cancelled:job['status']='paused'
                except Exception as e:job.update(status='error',error=str(e))
                finally:
                    job['updated_at']=time.time();self.store.put('job',ident,job);self.cancels.pop(ident,None)
            thread=threading.Thread(target=run,daemon=True);self.runners[ident]=thread;thread.start()
    def create_job(self,body):
        text=body.get('text');fmt=body.get('format','txt');title=body.get('title','名称未設定')
        if not isinstance(text,str) or not text.strip() or len(text)>500000:raise ValueError('原稿は1〜500,000文字で指定してください。')
        if not isinstance(title,str) or len(title)>200:raise ValueError('タイトルは200文字までです。')
        opts=options(body.get('options',self.settings()));segments=segment(text,fmt)
        if len(segments)>2000:raise ValueError('原稿の段落が多すぎます。分割してください。')
        for s in segments:s.update(translation='',status='pending',warnings=[])
        ident=uuid.uuid4().hex
        job={'id':ident,'title':title,'source':text,'format':fmt,'options':opts,'segments':segments,'status':'paused','created_at':time.time(),'updated_at':time.time(),'model_provenance':self.engine.provenance(opts['model'])}
        self.store.put('job',ident,job)
        if body.get('start',True):self.start_job(ident)
        return self.store.get('job',ident)
    def shutdown(self):
        for e in list(self.cancels.values()):e.set()
        self.engine.stop()
        for thread in list(self.runners.values()):
            if thread is not threading.current_thread():thread.join(timeout=10)

class Handler(BaseHTTPRequestHandler):
    server_version='PlamoLocal/0.1'
    def log_message(self,*args):pass  # Never log source text, tokens, or request bodies.
    @property
    def app(self):return self.server.app
    def _origin_ok(self):
        host=self.headers.get('Host','')
        if host not in LOCAL_HOSTS:return False
        origin=self.headers.get('Origin')
        return not origin or origin in LOCAL_ORIGINS or bool(re.fullmatch(r'chrome-extension://[a-p]{32}',origin))
    def _headers(self,status,kind='application/json; charset=utf-8',length=None):
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',f"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self' http://127.0.0.1:{API_PORT} http://localhost:{API_PORT}; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        origin=self.headers.get('Origin')
        if origin and self._origin_ok():self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Vary','Origin')
        if length is not None:self.send_header('Content-Length',str(length))
        self.end_headers()
    def json(self,data,status=200):
        value=json.dumps(data,ensure_ascii=False).encode();self._headers(status,length=len(value));self.wfile.write(value)
    def do_OPTIONS(self):
        if not self._origin_ok():self.json({'error':'許可されていない接続元です。'},403);return
        self.send_response(204);self.send_header('Access-Control-Allow-Origin',self.headers.get('Origin',f'http://127.0.0.1:{API_PORT}'));self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type');self.send_header('Access-Control-Allow-Methods','GET, POST, DELETE, OPTIONS');self.end_headers()
    def body(self):
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:raise ValueError('Content-Lengthが不正です。')
        if not 0<length<=4_000_000:raise ValueError('リクエストが大きすぎるか空です。')
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('JSONで送信してください。')
        body=json.loads(self.rfile.read(length))
        if not isinstance(body,dict):raise ValueError('JSONオブジェクトが必要です。')
        return body
    def dispatch(self):
        if not self._origin_ok():self.json({'error':'接続元またはHostが許可されていません。'},403);return
        parsed=urlsplit(self.path);path=parsed.path
        if path=='/api/health' and self.command=='GET':self.json({'ok':True,'version':'0.1.4'});return
        if path=='/api/bootstrap' and self.command=='GET':
            if self.headers.get('Sec-Fetch-Site') in {'same-origin','none'} and self.headers.get('Origin',f'http://127.0.0.1:{API_PORT}') in LOCAL_ORIGINS:self.json({'token':self.app.token});return
            self.json({'error':'ローカルの原稿画面から接続してください。'},403);return
        if not path.startswith('/api/'):
            if self.command!='GET':self.json({'error':'見つかりません。'},404);return
            name=path.lstrip('/') or 'app.html';base=self.app.root/'dist';file=(base/name).resolve()
            if not file.is_relative_to(base.resolve()) or not file.is_file():self.json({'error':'画面がありません。npm run buildを実行してください。'},404);return
            value=file.read_bytes();self._headers(200,mimetypes.guess_type(str(file))[0] or 'application/octet-stream',len(value));self.wfile.write(value);return
        auth=self.headers.get('Authorization','')
        if not hmac.compare_digest(auth,'Bearer '+self.app.token):self.json({'error':'接続キーを確認してください。'},401);return
        parts=path.split('/')[2:];method=self.command;body=self.body() if method=='POST' else {}
        if parts==['state'] and method=='GET':
            jobs=[{k:j[k] for k in ['id','title','status','format','updated_at']}|{'total':len(j['segments']),'completed':sum(s['status']=='done' for s in j['segments'])} for j in self.app.store.list('job')]
            self.json({'engine':self.app.engine.status(),'settings':self.app.settings(),'jobs':jobs,'profiles':self.app.store.list('profile')});return
        if parts==['settings']:
            if method=='GET':self.json(self.app.settings());return
            if method=='POST':
                theme=body.get('theme','system')
                if theme not in {'light','dark','system'}:raise ValueError('表示設定が不正です。')
                value={**options(body),'theme':theme};self.app.store.put('config','settings',value);self.json(value);return
        if parts==['models','load'] and method=='POST':
            model=body.get('model')
            if model not in {'2b','8b'}:raise ValueError('モデルが不明です。')
            def load():
                try:self.app.engine.load(model)
                except Exception:pass
            threading.Thread(target=load,daemon=True).start();self.json({'accepted':True},202);return
        if parts==['models','stop'] and method=='POST':
            for event in list(self.app.cancels.values()):event.set()
            threading.Thread(target=self.app.engine.stop,daemon=True).start();self.json({'accepted':True},202);return
        if parts==['translations'] and method=='POST':
            text=body.get('text')
            if not isinstance(text,str) or not 0<len(text.strip())<=8000:raise ValueError('選択範囲は1〜8,000文字にしてください。')
            self.json(copy.deepcopy(self.app.start_translation(text,options(body.get('options',self.app.settings())))),202);return
        if len(parts)>=2 and parts[0]=='translations':
            ident=parts[1];task=self.app.tasks.get(ident)
            if not task:raise KeyError('翻訳が見つかりません。')
            if method=='GET':self.json(copy.deepcopy(task));return
            if parts[2:]==['cancel'] and method=='POST':
                if ident in self.app.cancels:self.app.cancels[ident].set()
                self.json({'accepted':True});return
        if parts==['jobs'] and method=='POST':self.json(self.app.create_job(body),201);return
        if len(parts)>=2 and parts[0]=='jobs':
            ident=parts[1];job=self.app.store.get('job',ident)
            if not job:raise KeyError('原稿が見つかりません。')
            if len(parts)==2 and method=='GET':self.json(job);return
            if len(parts)==2 and method=='DELETE':
                if ident in self.app.cancels:raise ValueError('先に原稿の処理を停止してください。')
                self.app.store.delete('job',ident);self.json({'deleted':True});return
            if parts[2:]==['cancel'] and method=='POST':
                if ident in self.app.cancels:self.app.cancels[ident].set()
                self.json({'accepted':True});return
            if parts[2:] in [['resume'],['retry']] and method=='POST':self.app.start_job(ident,retry=parts[2]=='retry');self.json({'accepted':True});return
            if parts[2:]==['export'] and method=='GET':
                kind=parse_qs(parsed.query).get('format',['json'])[0]
                if kind=='json':self.json(export_bundle(job));return
                if kind=='md':
                    value=export_markdown(job).encode();self._headers(200,'text/markdown; charset=utf-8',len(value));self.wfile.write(value);return
                if kind=='translated':
                    value=''.join((s['translation'] if s['status']=='done' else s['source'])+s['separator'] for s in job['segments']).encode()
                    self._headers(200,'text/plain; charset=utf-8',len(value));self.wfile.write(value);return
                raise ValueError('出力形式が不明です。')
        if parts==['profiles'] and method=='POST':
            name=body.get('name','')
            if not isinstance(name,str) or not name.strip() or len(name)>100:raise ValueError('設定名は1〜100文字で指定してください。')
            profile={'id':uuid.uuid4().hex,'name':name,'options':options(body.get('options',{}))};self.app.store.put('profile',profile['id'],profile);self.json(profile,201);return
        if len(parts)==2 and parts[0]=='profiles' and method=='DELETE':self.app.store.delete('profile',parts[1]);self.json({'deleted':True});return
        if parts==['cache'] and method=='DELETE':self.app.store.clear_cache();self.json({'deleted':True});return
        if parts==['data'] and method=='DELETE':
            if self.app.cancels:raise ValueError('処理を停止してからデータを削除してください。')
            self.app.store.clear();self.app.tasks.clear();self.json({'deleted':True});return
        self.json({'error':'見つかりません。'},404)
    def handle_request(self):
        try:self.dispatch()
        except (ValueError,json.JSONDecodeError) as e:self.json({'error':str(e)},400)
        except KeyError as e:self.json({'error':str(e)},404)
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as e:self.json({'error':'処理に失敗しました: '+str(e)},500)
    do_GET=do_POST=do_DELETE=handle_request

def main():
    root=Path(__file__).resolve().parents[2];data=Path(os.environ.get('PLAMO_DATA_DIR',str(root/'.data'))).resolve()
    app=App(root,data);server=ThreadingHTTPServer(('127.0.0.1',API_PORT),Handler);server.app=app
    atexit.register(app.shutdown)
    print(f'PLaMo Local: http://127.0.0.1:{API_PORT}/app.html',flush=True)
    print('接続キーは操作アプリ、または scripts/start.py から取得してください。',flush=True)
    signal.signal(signal.SIGTERM,lambda *_:threading.Thread(target=server.shutdown,daemon=True).start())
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close();app.shutdown()
if __name__=='__main__':main()
