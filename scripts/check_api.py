import os
"""Black-box security and round-trip checks against the running real service."""
from pathlib import Path
import json, urllib.error, urllib.request
ROOT=Path(__file__).resolve().parents[1];token=(ROOT/'.data/token').read_text().strip();results=[]
def check(name,path,status,method='GET',body=None,headers=None):
    data=json.dumps(body).encode() if body is not None else None
    try:
        request=urllib.request.Request(f'http://127.0.0.1:{os.environ.get("PLAMO_API_PORT","8765")}'+path,data=data,method=method,headers=headers or {})
        with urllib.request.urlopen(request,timeout=10) as r:actual=r.status
    except urllib.error.HTTPError as e:actual=e.code
    results.append({'name':name,'expected':status,'actual':actual});assert actual==status,(name,actual,status)
check('health','/api/health',200)
check('unauthenticated state','/api/state',401)
check('cross-origin bootstrap','/api/bootstrap',403,headers={'Origin':'https://example.org','Sec-Fetch-Site':'cross-site'})
check('no browser context bootstrap','/api/bootstrap',403)
check('DNS rebinding host','/api/health',403,headers={'Host':'evil.example:8765'})
check('authenticated state','/api/state',200,headers={'Authorization':'Bearer '+token})
check('bad model rejected','/api/models/load',400,'POST',{'model':'other'},{'Authorization':'Bearer '+token,'Content-Type':'application/json'})
check('wrong content type','/api/translations',400,'POST',{'text':'Test'},{'Authorization':'Bearer '+token,'Content-Type':'text/plain'})
check('path traversal','/../runtime-manifest.json',404)
(ROOT/'work/api-security.json').write_text(json.dumps(results,indent=2));print(f'{len(results)} API checks passed')
