import os
"""Real GPU benchmark through the authenticated application API, not a stub."""
from pathlib import Path
import json,statistics,time,urllib.request
ROOT=Path(__file__).resolve().parents[1];TOKEN=(ROOT/'.data/token').read_text().strip()
def api(path,body=None):
    request=urllib.request.Request(f'http://127.0.0.1:{os.environ.get("PLAMO_API_PORT","8765")}/api/'+path,data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+TOKEN,'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=240) as r:return json.load(r)
def translation(text,opts):
    task=api('translations',{'text':text,'options':opts})
    for _ in range(1800):
        task=api('translations/'+task['id'])
        if task['status'] in {'done','error','cancelled'}:return task
        time.sleep(.05)
    raise TimeoutError('Translation did not finish')
if __name__=='__main__':
    report={'hardware':'RTX 4090 24564 MiB / Core i9-14900KF / WSL2','runtime':'b12121, locally built CUDA 12.6, sm89, context 16384, Q4_K_M','application_cache':'cleared before each run','native_prompt_cache':True,'repeats':3,'results':[]}
    for model in ['2b','8b']:
        api('models/load',{'model':model})
        for _ in range(600):
            engine=api('state')['engine']
            if engine['state']=='ready' and engine['model']==model:break
            if engine['state']=='error':raise RuntimeError(engine['error'])
            time.sleep(.2)
        else:raise TimeoutError('Model load')
        for name,text,source,target in [('short_en_ja','Our results suggest that the proposed method improves accuracy by 12.5%. However, the effect was not statistically significant.','en','ja'),('paper_ja_en',(ROOT/'samples/paper.md').read_text(),'ja','en'),('long_ja_en','\n\n'.join(f'実験{i+1}では、提案手法を{120+i}件のデータで評価した。平均精度は92.5%であり、ベースラインより2.1ポイント高かった。ただし、この差は統計的に有意ではなかった。結果は改善の可能性を示唆するが、因果関係を証明するものではない。今後は別のデータセットと異なる実験条件でも再現性を検証する必要がある。' for i in range(18)),'ja','en')]:
            times=[];outputs=[]
            for repeat in range(3):
                request=urllib.request.Request(f'http://127.0.0.1:{os.environ.get("PLAMO_API_PORT","8765")}/api/cache',method='DELETE',headers={'Authorization':'Bearer '+TOKEN})
                urllib.request.urlopen(request).close()
                opts={'model':model,'source_lang':source,'target_lang':target,'domain':'学術論文','context':'忠実な学術論文の下訳。','glossary':[{'source':'提案手法','target':'proposed method'}] if source=='ja' else []}
                task=translation(text,opts)
                if task['status']!='done':raise RuntimeError(task)
                times.append(task['metrics']);outputs.append(task['translation'])
            row={'model':model,'sample':name,'source':text,'load_seconds':engine['load_seconds'],'runs':times,'median_seconds':statistics.median(v['elapsed_seconds'] for v in times),'median_ttft_seconds':statistics.median(v['ttft_seconds'] for v in times),'translation':outputs[-1],'warnings':task['warnings']}
            report['results'].append(row);print(model,name,row['median_seconds'],'sec',row['warnings'],flush=True)
            (ROOT/'work/benchmark.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('Saved work/benchmark.json',flush=True)
