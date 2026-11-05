import os
from pathlib import Path
import json,subprocess,sys,time,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parents[1]
def api(path,body=None):
    token=(ROOT/'.data/token').read_text().strip()
    r=urllib.request.Request(f'http://127.0.0.1:{os.environ.get("PLAMO_API_PORT","8765")}/api/'+path,data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with urllib.request.urlopen(r,timeout=30) as response:return json.load(response)
text='\n\n'.join(f'実験{i+1}では、提案手法を{120+i}件のデータで評価した。結果は改善の可能性を示唆するが、因果関係を証明するものではない。' for i in range(24))
request=urllib.request.Request(f'http://127.0.0.1:{os.environ.get("PLAMO_API_PORT","8765")}/api/cache',method='DELETE',headers={'Authorization':'Bearer '+(ROOT/'.data/token').read_text().strip()});urllib.request.urlopen(request).close()
job=api('jobs',{'title':'API再起動の検証','text':text,'format':'txt','options':{'model':'2b','source_lang':'ja','target_lang':'en'}})
for _ in range(400):
    job=api('jobs/'+job['id'])
    if job['status']=='running' and sum(s['status']=='done' for s in job['segments'])>=2:break
    time.sleep(.02)
else:raise RuntimeError('Could not interrupt a partially completed job')
before={s['id']:s['translation'] for s in job['segments'] if s['status']=='done'}
subprocess.run([sys.executable,str(ROOT/'scripts/stop.py')],check=True)
for _ in range(150):
    try:api('health');time.sleep(.1)
    except Exception:break
else:raise RuntimeError('API did not stop')
subprocess.run([sys.executable,str(ROOT/'scripts/start.py'),'--quiet'],check=True)
recovered=api('jobs/'+job['id']);assert recovered['status']=='paused',recovered['status']
completed_before=sum(s['status']=='done' for s in recovered['segments'])
api('jobs/'+job['id']+'/resume',{})
for _ in range(900):
    job=api('jobs/'+job['id'])
    if job['status'] in {'done','error'}:break
    time.sleep(.1)
assert job['status']=='done',job.get('error',job['status'])
assert all(next(s for s in job['segments'] if s['id']==ident)['translation']==text for ident,text in before.items())
assert ''.join(s['source']+s['separator'] for s in job['segments'])==text
try:
    request=urllib.request.Request(f'http://127.0.0.1:{os.environ.get("PLAMO_INFERENCE_PORT","8766")}/completion',data=b'{"prompt":"test","n_predict":1}',headers={'Content-Type':'application/json'})
    urllib.request.urlopen(request);raise AssertionError('Unauthenticated raw inference was accepted')
except urllib.error.HTTPError as error:assert error.code==401,error.code
record={'recovered_status':recovered['status'],'completed_before_stop':len(before),'completed_before_resume':completed_before,'completed_translations_preserved':True,'completed_after_resume':len(job['segments']),'source_roundtrip':True,'raw_inference_unauthenticated_status':401}
(ROOT/'work/restart.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
