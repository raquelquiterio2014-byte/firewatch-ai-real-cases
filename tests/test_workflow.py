import copy
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from core import catalogue, timestamp, validate_evidence, analyze, Store, export_bundle

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.e=dict(id='TEST-ONLY',case_id='FW-RC-001',claim='Synthetic test observation; not a historical claim.',source_url='https://example.org/test-only',locator='test fixture',observed_at='2018-11-08T12:00:00Z',available_at='2018-11-08T12:30:00Z',verification_note='Synthetic unit-test fixture',reviewer='Test',topic='fire',source_role='contemporaneous_record',verified=True,conflict=False)
    def run_case(self,items):return analyze('FW-RC-001','2018-11-08T13:00:00Z',items)
    def test_catalogue_integrity(self):
        cases=catalogue();self.assertEqual(len(cases),10);self.assertEqual(len({c['id'] for c in cases}),10)
        self.assertEqual(sum(len(c['sources']) for c in cases),15)
        self.assertTrue(all(s['role']=='research_only' for c in cases for s in c['sources']))
    def test_timezone_required(self):
        with self.assertRaises(ValueError):timestamp('2018-11-08T13:00:00')
    def test_equivalent_offsets(self):self.assertEqual(timestamp('2018-11-08T10:00:00-03:00'),timestamp('2018-11-08T13:00:00Z'))
    def test_observation_cannot_follow_availability(self):
        e=dict(self.e,observed_at='2018-11-09T00:00:00Z')
        with self.assertRaises(ValueError):validate_evidence(e)
    def test_research_source_rejected(self):
        with self.assertRaises(ValueError):validate_evidence(dict(self.e,source_role='research_only'))
    def test_empty_blocks(self):self.assertEqual(self.run_case([])['status'],'BLOCKED_NO_ADMISSIBLE_EVIDENCE')
    def test_unverified_excluded(self):self.assertEqual(self.run_case([dict(self.e,verified=False)])['excluded_evidence'][0]['reason'],'UNVERIFIED')
    def test_future_publication_excluded(self):self.assertEqual(self.run_case([dict(self.e,available_at='2021-01-01T00:00:00Z')])['excluded_evidence'][0]['reason'],'AFTER_CUTOFF')
    def test_exact_cutoff_included(self):self.assertEqual(len(self.run_case([dict(self.e,available_at='2018-11-08T13:00:00Z')])['admitted_evidence']),1)
    def test_wrong_case_excluded(self):self.assertEqual(self.run_case([dict(self.e,case_id='FW-RC-002')])['excluded_evidence'][0]['reason'],'WRONG_CASE')
    def test_partial_dossier_not_severity(self):
        r=self.run_case([self.e]);self.assertEqual(r['status'],'PARTIAL_DOSSIER');self.assertEqual(r['severity'],'NOT_ESTIMATED')
    def test_conflict_holds(self):self.assertEqual(self.run_case([dict(self.e,conflict=True)])['status'],'HOLD_CONFLICT')
    def test_complete_still_human_review(self):
        r=self.run_case([dict(self.e,id=str(i),topic=t) for i,t in enumerate(['fire','weather','access','exposure'])])
        self.assertEqual(r['status'],'READY_FOR_HUMAN_RESEARCH_REVIEW');self.assertEqual(r['human_review'],'PENDING');self.assertEqual(len(r['trace']),8)
        self.assertFalse(r['trace'][5]['output']['operational_use'])
    def test_run_hash(self):
        r=self.run_case([self.e]);digest=r.pop('content_sha256')
        self.assertEqual(hashlib.sha256(json.dumps(r,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),digest)
    def test_persistence_review_export_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'db.sqlite';s=Store(db);e=s.add_evidence(self.e);r=self.run_case([e]);s.save_run(r)
            s.add_evidence(dict(self.e,claim='Another synthetic fixture'))
            s.review(r['id'],'Researcher','REQUEST_CORRECTION','Missing context')
            self.assertEqual(len(s.runs('FW-RC-001')[0]['admitted_evidence']),1)
            s.db.close();s=Store(db)
            self.assertEqual(len(s.evidence('FW-RC-001')),2)
            out=Path(d)/'bundle.zip';export_bundle(s,'FW-RC-001',out)
            with zipfile.ZipFile(out) as z:
                for line in z.read('SHA256SUMS.txt').decode().splitlines():
                    digest,name=line.split('  ',1);self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),digest)
                self.assertEqual(json.loads(z.read('reviews.json'))[0]['run_id'],r['id'])
            s.db.close()
    def test_unknown_review_run_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)/'db.sqlite')
            with self.assertRaises(ValueError):s.review('missing','Test','ACCEPT_RESEARCH_RECORD','Test')
            s.db.close()

if __name__=='__main__':unittest.main()
