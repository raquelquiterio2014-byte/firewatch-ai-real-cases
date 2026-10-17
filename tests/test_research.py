import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from core import Store, catalogue, analyze, export_bundle
from gemini_gateway import GeminiGateway, RequestFailed
from research import research_seed, validate_research, initialize_research, evidence_for, analyze_research, run_batch, render_report, export_all_cases

class ResearchTests(unittest.TestCase):
 def test_ten_cases_thirty_records(self):
  rows=research_seed();self.assertEqual(len(rows),30);self.assertEqual(len({e['id'] for e in rows}),30)
  for case in catalogue():self.assertEqual(sum(e['case_id']==case['id'] for e in rows),3)
  for e in rows:validate_research(e)
 def test_source_audit_covers_every_seed(self):
  from core import ROOT
  audit=json.loads((ROOT/'data/source_audit.json').read_text())
  checks=[c for page in audit for c in page['checks']]
  self.assertEqual({c['id'] for c in checks},{e['id'] for e in research_seed()})
  self.assertTrue(all(c['anchor_matched'] for c in checks))
 def test_no_invented_timestamps(self):
  for e in research_seed():self.assertIsNone(e['observed_at']);self.assertIsNone(e['available_at']);self.assertFalse(e['original_availability_verified'])
 def test_fake_exact_time_rejected(self):
  e=dict(research_seed()[0],available_at='2018-11-08T12:00:00Z')
  with self.assertRaises(ValueError):validate_research(e)
 def test_original_cutoff_rejects_research_seed(self):
  r=analyze('FW-RC-001','2018-11-08T23:00:00Z',research_seed()[:3]);self.assertEqual(r['status'],'BLOCKED_NO_ADMISSIBLE_EVIDENCE');self.assertEqual(len(r['admitted_evidence']),0)
 def test_document_mode_accepts_post_event_report(self):
  r=analyze_research('FW-RC-001',research_seed()[:3]);self.assertEqual(r['status'],'RETROSPECTIVE_DOCUMENT_ANALYSIS_COMPLETED');self.assertIsNone(r['cutoff']);self.assertEqual(r['human_review'],'PENDING')
 def test_review_date_cannot_precede_curation(self):
  r=analyze_research('FW-RC-001',research_seed()[:3],as_of='2026-10-16');self.assertEqual(r['status'],'BLOCKED_NO_RESEARCH_EVIDENCE')
 def test_missing_topics_informational(self):
  r=analyze_research('FW-RC-002',research_seed()[3:6]);self.assertIn('access',r['missing_topics']);self.assertEqual(r['status'],'RETROSPECTIVE_DOCUMENT_ANALYSIS_COMPLETED');self.assertEqual(r['severity'],'NOT_ESTIMATED')
 def test_source_independence_not_claim_count(self):
  r=analyze_research('FW-RC-001',research_seed()[:3]);ctx=r['report']['context'];self.assertEqual(ctx['record_count'],3);self.assertEqual(ctx['source_count'],1)
 def test_wrong_case_rejected(self):
  r=analyze_research('FW-RC-002',research_seed()[:3]);self.assertEqual(len(r['admitted_evidence']),0)
 def test_flagged_conflict_holds(self):
  e=dict(research_seed()[0],conflict=True);self.assertEqual(analyze_research('FW-RC-001',[e])['status'],'HOLD_CONFLICT')
 def test_seed_idempotent_and_old_records_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   s=Store(Path(d)/'db');initialize_research(s);initialize_research(s)
   self.assertEqual(s.db.execute('SELECT count(*) FROM research_evidence').fetchone()[0],30)
   self.assertEqual(s.db.execute('SELECT count(*) FROM evidence').fetchone()[0],0);s.db.close()
 def test_all_ten_run_offline(self):
  rows=research_seed();cases=catalogue();mapped={c['id']:[e for e in rows if e['case_id']==c['id']] for c in cases};results=run_batch(cases,mapped)
  self.assertEqual(len(results),10);self.assertTrue(all(r['status']=='RETROSPECTIVE_DOCUMENT_ANALYSIS_COMPLETED' for r in results))
  self.assertTrue(all(len(r['report']['supported_findings'])==3 for r in results));self.assertTrue(all(r['severity']=='NOT_ESTIMATED' for r in results))
 def test_gemini_research_prompt_labels_hindsight(self):
  prompts=[]
  def transport(url,payload,key,timeout):
   prompt=json.loads(payload['contents'][0]['parts'][0]['text']);prompts.append(prompt);e=prompt['admitted_claims'][0]
   output={'findings':[{'evidence_id':e['id'],'excerpt':e['claim'],'interpretation':'Research interpretation requiring human review.'}],'gaps':[],'cautions':[],'needs_review':True}
   return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(output)}]}}]}
  r=analyze_research('FW-RC-001',research_seed()[:3],GeminiGateway('fake-key-123456789012345',transport=transport))
  self.assertEqual(r['mode'],'llm_assisted');self.assertEqual(len(prompts),2)
  self.assertIn('NOT a responder-time cutoff',prompts[0]['task_context']);self.assertEqual(prompts[1]['previous_analysis'],r['llm']['evidence']['output'])
 def test_persistent_quota_pauses_later_external_calls(self):
  calls=[]
  def transport(*args):calls.append(1);raise RequestFailed('HTTP_429',True)
  cases=catalogue();rows=research_seed();mapped={c['id']:[e for e in rows if e['case_id']==c['id']] for c in cases}
  results=run_batch(cases,mapped,GeminiGateway('fake-key-123456789012345',transport=transport,sleep=lambda _:None))
  self.assertEqual(len(calls),6);self.assertEqual(len(results),10);self.assertEqual(results[1]['llm']['evidence']['attempts'],0);self.assertEqual(results[1]['llm']['evidence']['reason'],'BATCH_API_PAUSED_HTTP_429')
 def test_research_export_contains_readable_report(self):
  with tempfile.TemporaryDirectory() as d:
   s=Store(Path(d)/'db');initialize_research(s);r=analyze_research('FW-RC-001',evidence_for(s,'FW-RC-001'));s.save_run(r)
   s.review(r['id'],'Reviewer','REQUEST_CORRECTION','Pending raw record checks')
   out=Path(d)/'case.zip';export_bundle(s,'FW-RC-001',out)
   with zipfile.ZipFile(out) as z:
    self.assertEqual(len(json.loads(z.read('research_evidence.json'))),3);self.assertIn('reports/'+r['id']+'.txt',z.namelist());self.assertIn('NIST',z.read('reports/'+r['id']+'.txt').decode())
   allout=Path(d)/'all.zip';export_all_cases(s,allout)
   with zipfile.ZipFile(allout) as z:self.assertEqual(sum(n.endswith('.zip') for n in z.namelist()),10)
   s.db.close()
 def test_report_preserves_source_and_limitations(self):
  r=analyze_research('FW-RC-001',research_seed()[:3]);text=render_report(r);self.assertIn(research_seed()[0]['source_url'],text);self.assertIn('not historical model validation',text)

if __name__=='__main__':unittest.main()
