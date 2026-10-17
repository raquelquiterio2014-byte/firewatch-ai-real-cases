import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from core import Store, ROOT, analyze, validate_evidence, export_bundle
from pilot import dataset, dataset_digest, technical_review, technical_status, verify_artifacts, artifact_path, availability_bounds, analyze_pilot, initialize_pilot, save_human_review
from gemini_gateway import GeminiGateway

class PilotTests(unittest.TestCase):
 def test_three_downloaded_products_and_six_claims(self):
  d=dataset();self.assertEqual(len(d['products']),3);self.assertEqual(len(d['evidence']),6);self.assertTrue(all(c['status']=='MATCH' for c in verify_artifacts()))
 def test_technical_review_identity_not_human(self):
  r=technical_review();self.assertEqual(r['reviewer_kind'],'AI_ASSISTED_TECHNICAL_SOURCE_REVIEW');self.assertEqual(r['human_approval'],'PENDING');self.assertEqual(r['dataset_sha256'],dataset_digest())
 def test_exact_availability_never_fabricated(self):
  for p in dataset()['products']:self.assertFalse(p['exact_availability_verified']);self.assertIsNone(p['delivery_timezone']);self.assertFalse(p['version_delivery_link_verified'])
  for e in dataset()['evidence']:self.assertIsNone(e['available_at']);self.assertFalse(e['original_availability_verified'])
 def test_bounds_known_primary_source(self):
  b=availability_bounds(dataset()['products'][0]);self.assertEqual(b['lower'],'2022-07-16T10:40:00+00:00');self.assertEqual(b['upper'],'2022-07-17T07:23:29+00:00')
 def test_production_date_used_for_aoi02_upper(self):
  b=availability_bounds(dataset()['products'][1]);self.assertEqual(b['upper'],'2022-07-18T00:00:00+00:00')
 def test_early_cutoff_withholds_uncertain_interval(self):
  r=analyze_pilot('2022-07-17T00:00:00Z');self.assertEqual(r['admitted_evidence'],[]);self.assertEqual(r['status'],'BLOCKED_NO_ELIGIBLE_ORIGINAL_PRODUCTS')
 def test_primary_cutoff_only_landiras_fep(self):
  r=analyze_pilot();self.assertEqual({e['product_id'] for e in r['admitted_evidence']},{'P01'});self.assertEqual(len(r['excluded_evidence']),4)
 def test_boundary_upper_bound_included(self):
  r=analyze_pilot('2022-07-17T07:23:29Z');self.assertEqual(len(r['admitted_evidence']),2)
 def test_one_second_before_upper_bound_withheld(self):
  r=analyze_pilot('2022-07-17T07:23:28Z');self.assertEqual(len(r['admitted_evidence']),0)
 def test_later_cutoff_includes_all_three(self):
  r=analyze_pilot('2022-07-18T06:00:00Z');self.assertEqual(len(r['admitted_evidence']),6);self.assertFalse(r['strict_replay_eligible'])
 def test_strict_replay_stays_blocked(self):
  r=analyze_pilot('2022-07-18T06:00:00Z',strict=True);self.assertEqual(len(r['admitted_evidence']),0);self.assertTrue(all(p['reason']=='ORIGINAL_AVAILABILITY_NOT_INDEPENDENTLY_VERIFIED' for p in r['product_decisions']))
 def test_legacy_original_mode_rejects_curated_records(self):
  r=analyze('FW-RC-008','2022-07-18T06:00:00Z',dataset()['evidence']);self.assertEqual(len(r['admitted_evidence']),0)
 def test_source_paths_confined(self):
  with self.assertRaises(ValueError):artifact_path({'file':'../outside.pdf'})
 def test_corrupted_file_excluded(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);shutil.copytree(ROOT/'originals',root/'originals')
   p=dataset()['products'][0];(root/p['file']).write_bytes(b'changed')
   r=analyze_pilot(root=root);self.assertEqual(r['admitted_evidence'],[]);self.assertEqual(r['product_decisions'][0]['reason'],'ARTIFACT_INTEGRITY_FAILURE')
 def test_changed_dataset_invalidates_review(self):
  d=copy.deepcopy(dataset());d['evidence'][0]['claim']='Changed claim'
  r=analyze_pilot(data=d);self.assertEqual(r['admitted_evidence'],[]);self.assertEqual(r['product_decisions'][0]['reason'],'TECHNICAL_REVIEW_DATASET_MISMATCH')
 def test_original_temporal_warning_preserved(self):
  r=analyze_pilot();self.assertIn('PORTAL_PDF_CALENDAR_DATE_DIFFERENCE',r['product_decisions'][1]['warnings'])
 def test_excluded_exposure_not_sent_to_gemini(self):
  prompts=[]
  def transport(u,p,k,t):
   data=json.loads(p['contents'][0]['parts'][0]['text']);prompts.append(data);e=data['admitted_claims'][0]
   output={'findings':[{'evidence_id':e['id'],'excerpt':e['claim'],'interpretation':'Research interpretation needing review.'}],'gaps':[],'cautions':[],'needs_review':True}
   return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(output)}]}}]}
  r=analyze_pilot(gateway=GeminiGateway('test-key-not-real-987654321',transport=transport))
  self.assertEqual(r['mode'],'llm_assisted');self.assertEqual(len(prompts),2)
  self.assertNotIn('447',json.dumps(prompts));self.assertTrue(all(e['product_id']=='P01' for p in prompts for e in p['admitted_claims']))
  self.assertIn('not verified exact release',prompts[0]['task_context'])
 def test_no_casualty_or_risk_score(self):
  r=analyze_pilot();self.assertEqual(r['severity'],'NOT_ESTIMATED');self.assertEqual(r['human_review'],'PENDING');self.assertFalse(r['trace'][-3]['output']['operational_use'])
 def test_baseline_idempotent_without_human_review(self):
  with tempfile.TemporaryDirectory() as d:
   s=Store(Path(d)/'db');initialize_pilot(s);initialize_pilot(s)
   self.assertEqual(len(s.runs('FW-RC-008')),1);self.assertEqual(s.reviews('FW-RC-008-PILOT-BASELINE-v1'),[]);s.db.close()
 def test_human_acceptance_requires_checklist(self):
  with tempfile.TemporaryDirectory() as d:
   s=Store(Path(d)/'db');r=analyze_pilot();s.save_run(r)
   with self.assertRaises(ValueError):save_human_review(s,r['id'],'Reviewer','ACCEPT_RESEARCH_RECORD','Research only',{})
   checks=dict(source_files_checked=True,temporal_assumptions_understood=True,research_limits_understood=True)
   review=save_human_review(s,r['id'],'Reviewer','ACCEPT_RESEARCH_RECORD','Accepted the bounded research assumptions only.',checks)
   self.assertEqual(review['reviewer_kind'],'HUMAN_RESEARCHER');self.assertEqual(review['run_sha256'],r['content_sha256']);self.assertFalse(s.runs('FW-RC-008')[0]['strict_replay_eligible']);s.db.close()
 def test_blocked_run_cannot_be_accepted(self):
  with tempfile.TemporaryDirectory() as d:
   s=Store(Path(d)/'db');r=analyze_pilot('2022-07-17T00:00:00Z');s.save_run(r)
   checks=dict(source_files_checked=True,temporal_assumptions_understood=True,research_limits_understood=True)
   with self.assertRaises(ValueError):save_human_review(s,r['id'],'Reviewer','ACCEPT_RESEARCH_RECORD','Test',checks)
   s.db.close()
 def test_review_does_not_rewrite_original_run(self):
  with tempfile.TemporaryDirectory() as d:
   s=Store(Path(d)/'db');r=analyze_pilot();s.save_run(r)
   save_human_review(s,r['id'],'Reviewer','REQUEST_CORRECTION','Need version history.',{})
   self.assertEqual(s.runs('FW-RC-008')[0],r);s.db.close()
 def test_export_includes_originals_and_technical_review(self):
  import zipfile
  with tempfile.TemporaryDirectory() as d:
   s=Store(Path(d)/'db');r=analyze_pilot();s.save_run(r);out=Path(d)/'pilot.zip';export_bundle(s,'FW-RC-008',out)
   with zipfile.ZipFile(out) as z:
    self.assertIn('pilot/pilot_technical_review.json',z.namelist())
    for p in dataset()['products']:self.assertEqual(hashlib.sha256(z.read(p['file'])).hexdigest(),p['sha256'])
   s.db.close()

if __name__=='__main__':unittest.main()
