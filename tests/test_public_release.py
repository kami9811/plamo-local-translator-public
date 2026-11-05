from pathlib import Path
import json,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'))
from plamo_local.documents import export_bundle,export_markdown
from plamo_local.engine import options
class PublicRelease(unittest.TestCase):
    def test_export_is_self_contained_and_attributed(self):
        job={'id':'example','title':'Example','source':'原文','format':'txt','options':options({}),'status':'done','segments':[{'id':'p0001','source':'原文','translation':'Translation','separator':'','status':'done','warnings':[]}]}
        result=export_bundle(job);self.assertEqual(result['attribution']['notice'],'Built with PLaMo');self.assertIn('Article 4',result['attribution']['license_texts']['en']);self.assertIn('第4条',result['attribution']['license_texts']['ja']);self.assertIn('PLaMo Community License Agreement',export_markdown(job));self.assertEqual(result['segments'][0]['source'],'原文')
    def test_setup_requires_model_license_acceptance_before_work(self):
        result=subprocess.run([sys.executable,str(ROOT/'scripts/setup_runtime.py')],capture_output=True,text=True)
        self.assertEqual(result.returncode,2);self.assertIn('--accept-model-license',result.stderr);self.assertNotIn('DOWNLOADED',result.stdout)
    def test_ui_and_examples_identify_generated_content(self):
        for name in ['extension/public/app.html','extension/public/popup.html','extension/src/content.ts','NOTICE.md','README.md']:
            self.assertIn('Built with PLaMo',(ROOT/name).read_text(),name)
        sample=json.loads((ROOT/'samples/handoff.json').read_text());self.assertIn('license_texts',sample['attribution']);self.assertEqual(''.join(s['source']+s['separator'] for s in sample['segments']),sample['source_text'])
if __name__=='__main__':unittest.main()
