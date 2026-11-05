from pathlib import Path
import sys, tempfile, unittest, json, threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from plamo_local.documents import protect,segment,check_numbers,export_bundle,export_markdown
from plamo_local.engine import options,prompt_for
from plamo_local.store import Store
class Documents(unittest.TestCase):
    def test_protected_math_citations_links_and_injection(self):
        source=r'式 $x=2$ と \cite{smith2024}、https://example.org/path、`<script>alert(1)</script>`。'
        p=protect(source);self.assertNotIn('smith2024',p.text);self.assertEqual(p.restore(p.text),(source,[]))
        self.assertTrue(p.restore(p.text.replace(next(iter(p.values)),''))[1])
    def test_segmentation_roundtrip_long_and_structured(self):
        for source,fmt in [('A sentence. '*600+'\n\nTail\n','txt'),('# 見出し\n\n本文 $x=1$.\n\n```python\nprint(2)\n```\n','md'),(r'\section{序論}'+'\n\n本文 '+r'\cite{a2026}。'+'\n\n$$x=2$$\n','tex')]:
            parts=segment(source,fmt,100)
            self.assertEqual(''.join(p['source']+p['separator'] for p in parts),source)
            self.assertEqual(len(set(p['id'] for p in parts)),len(parts))
    def test_tex_comment_does_not_hide_following_prose(self):
        source='% keep this comment\n翻訳する本文。\n\n次の段落。'
        parts=segment(source,'tex')
        self.assertEqual(''.join(p['source']+p['separator'] for p in parts),source)
        self.assertTrue(parts[0]['skip'])
        self.assertTrue(any('翻訳する本文' in p['source'] and not p['skip'] for p in parts))
    def test_number_check(self):
        self.assertFalse(check_numbers('1,000 and 12.5%','1,000と12.5%'))
        self.assertTrue(check_numbers('12.5%','125%'))
    def test_options_and_prompt(self):
        o=options({'source_lang':'ja','target_lang':'en','domain':'論文','glossary':[{'source':'提案手法','target':'proposed method'}]})
        p=prompt_for('これは試験です。',o,[('先行文','Previous sentence')]);self.assertIn('<|plamo:tag|>context',p);self.assertIn('<|plamo:index|>提案手法<|plamo:item|>proposed method',p);self.assertIn('Previous sentence',p)
        with self.assertRaises(ValueError):options({'model':'other'})
        with self.assertRaises(ValueError):options({'glossary':[{'source':'x'}]})
    def test_export_roundtrip_and_hostile_markdown(self):
        job={'id':'sample','title':'Test','source':'```\n原文\n```','format':'md','options':options({}),'status':'done','segments':[{'id':'p0001','source':'```\n原文\n```','translation':'<script>alert(1)</script>','separator':'','status':'done','warnings':[]} ]}
        bundle=json.loads(json.dumps(export_bundle(job),ensure_ascii=False));self.assertEqual(bundle['source_text'],job['source']);self.assertEqual(bundle['segments'][0]['source'],job['segments'][0]['source']);self.assertIn('原文と下訳',bundle['review_instructions']);self.assertIn('    <script>',export_markdown(job))
    def test_store_survives_restart(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d));s.put('job','one',{'status':'paused','text':'原稿'});s.cache_put('one',{'translation':'draft'})
            s=Store(Path(d));self.assertEqual(s.get('job','one')['text'],'原稿');s.clear_cache();self.assertIsNone(s.cache_get('one'));self.assertIsNotNone(s.get('job','one'))
if __name__=='__main__':unittest.main()
