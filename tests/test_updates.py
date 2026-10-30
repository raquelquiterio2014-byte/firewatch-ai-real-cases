"""Offline provider fixtures; not a live Google Search or Gemini validation."""
import copy
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from core import Store, export_bundle, validate_evidence
from gemini_gateway import OutputInvalid, RequestFailed
from updates import (UpdateGateway, digest, parse_grounding, validate_review, run_update,
                     save_update, discovered_for, latest_update, render_update_report, search_document)

KEY='offline-fixture-secret-not-a-real-key-12345678'
CASE='FW-RC-008'
QUESTION='Find new research about this case.'

def search_raw(claim='Synthetic research statement A.', uri='https://example.org/synthetic-test'):
    return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':claim}]},
        'groundingMetadata':{'webSearchQueries':['synthetic fixture search'],
            'groundingChunks':[{'web':{'uri':uri,'title':'Synthetic fixture source'}}],
            'groundingSupports':[{'segment':{'text':claim},'groundingChunkIndices':[0]}],
            'searchEntryPoint':{'renderedContent':'<div>Provider search suggestions fixture</div>'}}}],
        'modelVersion':'gemini-2.5-flash','usageMetadata':{'totalTokenCount':12}}

def review_output(data, needs=False, issues=None, resolutions=None, gaps=None):
    record=data['records'][-1]
    return dict(needs_review=needs,summary='Synthetic fixture research assessment.',
        findings=[dict(evidence_id=record['id'],excerpt=record['claim'],interpretation='Synthetic fixture interpretation.')],
        issues=issues or [],resolutions=resolutions or [],gaps=gaps or [])

def api_output(output):
    return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(output)}]}}]}

class Fixture:
    def __init__(self,claim='Synthetic research statement A.',need=False,resolve=False,critic_need=None):
        self.claim,self.need,self.resolve,self.critic_need=claim,need,resolve,critic_need
        self.calls=[]
    def __call__(self,url,payload,key,timeout):
        self.calls.append(copy.deepcopy(payload))
        if 'tools' in payload:return search_raw(self.claim)
        data=json.loads(payload['contents'][0]['parts'][0]['text'])
        role=data['role']; record=data['records'][-1]
        need=self.need if role=='evidence' or self.critic_need is None else self.critic_need
        issues=[dict(issue_id='scope_gap',reason='Synthetic unresolved research scope.',evidence_ids=[record['id']])] if need else []
        resolutions=[dict(issue_id=k,reason='Synthetic new support for reassessment.',evidence_ids=[record['id']]) for k in data['previous_open_issues']] if self.resolve else []
        return api_output(review_output(data,needs=need,issues=issues,resolutions=resolutions))
    def gateway(self):return UpdateGateway(KEY,transport=self,sleep=lambda _:None)

class GroundingTests(unittest.TestCase):
    def test_search_tool_and_no_schema_on_discovery_request(self):
        fixture=Fixture();result=fixture.gateway().discover({'id':CASE,'name':'Fixture','country':'Test','period':'2022','research_question':'Test'},QUESTION)
        self.assertTrue(result['succeeded'])
        payload=fixture.calls[0]
        self.assertEqual(payload['tools'],[{'google_search':{}}])
        self.assertNotIn('responseSchema',payload['generationConfig'])
        self.assertEqual(result['source'],'injected_transport')

    def test_missing_queries_or_grounding_does_not_count_as_web_search(self):
        for key in ('webSearchQueries','groundingSupports','groundingChunks'):
            raw=search_raw();raw['candidates'][0]['groundingMetadata'][key]=[]
            with self.subTest(key=key),self.assertRaises((OutputInvalid,IndexError)):
                parse_grounding(raw,CASE,'2026-10-30T12:00:00Z')

    def test_hallucinated_segment_or_unknown_citation_is_rejected(self):
        for change in ('text','index'):
            raw=search_raw()
            support=raw['candidates'][0]['groundingMetadata']['groundingSupports'][0]
            if change=='text':support['segment']['text']='Not in the response'
            else:support['groundingChunkIndices']=[8]
            with self.subTest(change=change),self.assertRaises(OutputInvalid):parse_grounding(raw,CASE,'2026-10-30T12:00:00Z')

    def test_source_urls_reject_unsafe_targets(self):
        for uri in ('http://example.org','https://localhost/x','https://127.0.0.1/x','https://user:secret@example.org/x','https://example.org:8080/x','javascript:alert(1)'):
            with self.subTest(uri=uri),self.assertRaises(OutputInvalid):parse_grounding(search_raw(uri=uri),CASE,'2026-10-30T12:00:00Z')

    def test_search_passages_are_not_claimed_original_or_contemporaneous(self):
        result=parse_grounding(search_raw(),CASE,'2026-10-30T12:00:00Z')
        record=result['records'][0]
        self.assertEqual(record['source_role'],'search_grounded_synthesis')
        self.assertIsNone(record['available_at']);self.assertIsNone(record['source_published_on'])
        self.assertFalse(record['original_availability_verified'])
        with self.assertRaises(ValueError):validate_evidence(record)

    def test_bad_search_key_never_calls_transport(self):
        gateway=UpdateGateway('',transport=lambda *args:self.fail('Network called'))
        result=gateway.discover({'id':CASE,'name':'Fixture','country':'Test','period':'2022','research_question':'Test'},QUESTION)
        self.assertEqual(result['reason'],'MISSING_KEY');self.assertEqual(result['attempts'],0)

    def test_secret_echo_is_rejected_and_not_exported(self):
        gateway=UpdateGateway(KEY,transport=lambda *args:search_raw(KEY))
        result=gateway.discover({'id':CASE,'name':'Fixture','country':'Test','period':'2022','research_question':'Test'},QUESTION)
        self.assertFalse(result['succeeded']);self.assertNotIn(KEY,json.dumps(result))

    def test_retry_is_bounded_and_error_bodies_are_hidden(self):
        calls=[]
        def failed(*args):calls.append(1);raise RequestFailed('HTTP_429',True)
        result=UpdateGateway(KEY,transport=failed,sleep=lambda _:None).discover({'id':CASE,'name':'Fixture','country':'Test','period':'2022','research_question':'Test'},QUESTION)
        self.assertEqual(len(calls),3);self.assertEqual(result['reason'],'HTTP_429')
        self.assertFalse(result['succeeded'])

class UpdateCycleTests(unittest.TestCase):
    def test_each_refresh_makes_fresh_search_and_dependent_critic(self):
        fixture=Fixture();first=run_update(CASE,QUESTION,fixture.gateway())
        second=run_update(CASE,QUESTION,fixture.gateway(),first['new_records'],first)
        self.assertEqual(len(fixture.calls),6)
        self.assertEqual(second['new_record_ids'],[])
        critic=json.loads(fixture.calls[2]['contents'][0]['parts'][0]['text'])
        self.assertIsNotNone(critic['evidence_assessment'])
        self.assertNotEqual(first['id'],second['id'])

    def test_routine_update_can_report_no_intervention_without_approval(self):
        result=run_update(CASE,QUESTION,Fixture().gateway())
        self.assertEqual(result['review_assessment']['recommendation'],'NOT_REQUESTED')
        self.assertEqual(result['human_review'],'NOT_REQUESTED_NOT_APPROVED')
        self.assertFalse(result['review_assessment']['operational_use'])
        self.assertEqual(result['severity'],'NOT_ESTIMATED')

    def test_either_agent_can_require_review(self):
        for fixture in (Fixture(need=True),Fixture(need=False,critic_need=True)):
            result=run_update(CASE,QUESTION,fixture.gateway())
            self.assertEqual(result['review_assessment']['recommendation'],'REQUIRED')
            self.assertTrue(result['review_assessment']['open_issues'])

    def test_no_new_record_cannot_silently_close_an_issue(self):
        first=run_update(CASE,QUESTION,Fixture(need=True).gateway())
        later=run_update(CASE,QUESTION,Fixture(resolve=True).gateway(),first['new_records'],first)
        self.assertEqual(later['review_assessment']['recommendation'],'REQUIRED')
        self.assertIn('scope_gap',later['review_assessment']['open_issues'])

    def test_new_evidence_and_both_agents_can_reassess_prior_issue(self):
        first=run_update(CASE,QUESTION,Fixture(need=True).gateway())
        original=copy.deepcopy(first)
        later=run_update(CASE,QUESTION,Fixture(claim='Synthetic new research statement B.',resolve=True).gateway(),first['new_records'],first)
        self.assertEqual(later['review_assessment']['recommendation'],'NOT_REQUESTED')
        self.assertEqual(later['review_assessment']['previous_recommendation'],'REQUIRED')
        self.assertEqual(later['review_assessment']['resolved_issues'][0]['issue_id'],'scope_gap')
        self.assertEqual(first,original)
        self.assertEqual(later['previous_run_sha256'],first['content_sha256'])

    def test_one_agent_resolution_without_critic_support_is_insufficient(self):
        first=run_update(CASE,QUESTION,Fixture(need=True).gateway())
        fixture=Fixture(claim='Synthetic new research statement B.',resolve=True)
        def transport(url,payload,key,timeout):
            raw=fixture(url,payload,key,timeout)
            if 'tools' not in payload and json.loads(payload['contents'][0]['parts'][0]['text'])['role']=='critic':
                output=json.loads(raw['candidates'][0]['content']['parts'][0]['text']);output['resolutions']=[];return api_output(output)
            return raw
        later=run_update(CASE,QUESTION,UpdateGateway(KEY,transport=transport),first['new_records'],first)
        self.assertEqual(later['review_assessment']['recommendation'],'REQUIRED')

    def test_invalid_citation_or_flag_does_not_downgrade_review(self):
        fixture=Fixture()
        for kind in ('citation','boolean'):
            def transport(url,payload,key,timeout):
                raw=fixture(url,payload,key,timeout)
                if 'tools' not in payload:
                    output=json.loads(raw['candidates'][0]['content']['parts'][0]['text'])
                    if kind=='citation':output['findings'][0]['evidence_id']='invented'
                    else:output['needs_review']='false'
                    return api_output(output)
                return raw
            result=run_update(CASE,QUESTION,UpdateGateway(KEY,transport=transport))
            self.assertEqual(result['review_assessment']['recommendation'],'REQUIRED')
            self.assertEqual(result['mode'],'explicit_fallback')

    def test_generic_review_request_is_retained_as_an_open_issue(self):
        fixture=Fixture()
        def transport(url,payload,key,timeout):
            raw=fixture(url,payload,key,timeout)
            if 'tools' not in payload:
                data=json.loads(payload['contents'][0]['parts'][0]['text'])
                return api_output(review_output(data,needs=True))
            return raw
        first=run_update(CASE,QUESTION,UpdateGateway(KEY,transport=transport))
        later=run_update(CASE,QUESTION,Fixture(claim='Synthetic new statement B.').gateway(),first['new_records'],first)
        self.assertEqual(later['review_assessment']['recommendation'],'REQUIRED')
        self.assertIn('EVIDENCE_REVIEW_REQUEST',later['review_assessment']['open_issues'])

    def test_failure_preserves_old_records_and_requires_review(self):
        first=run_update(CASE,QUESTION,Fixture(need=True).gateway())
        later=run_update(CASE,QUESTION,UpdateGateway(''),first['new_records'],first)
        self.assertEqual(later['admitted_evidence'],first['admitted_evidence'])
        self.assertEqual(later['new_record_ids'],[])
        self.assertEqual(later['review_assessment']['recommendation'],'REQUIRED')

    def test_wrong_case_invalid_question_or_tampered_parent_is_rejected(self):
        first=run_update(CASE,QUESTION,Fixture().gateway())
        with self.assertRaises(ValueError):run_update('FW-RC-001',QUESTION,Fixture().gateway(),previous=first)
        with self.assertRaises(ValueError):run_update(CASE,'',Fixture().gateway())
        first['review_assessment']['summary']='Tampered'
        with self.assertRaises(ValueError):run_update(CASE,QUESTION,Fixture().gateway(),previous=first)

    def test_request_schema_allows_review_reassessment_only_in_new_mode(self):
        fixture=Fixture();run_update(CASE,QUESTION,fixture.gateway())
        for payload in fixture.calls[1:]:
            self.assertNotIn('tools',payload)
            self.assertEqual(payload['generationConfig']['responseMimeType'],'application/json')
        from gemini_gateway import validate_output
        with self.assertRaises(OutputInvalid):validate_output({'findings':[],'gaps':[],'cautions':[],'needs_review':False},[])

class PersistenceTests(unittest.TestCase):
    def test_restart_deduplication_and_separate_human_review(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'db';store=Store(path)
            first=run_update(CASE,QUESTION,Fixture().gateway());save_update(store,first)
            store.review(first['id'],'Fixture reviewer','REQUEST_CORRECTION','Test review only')
            store.db.close();store=Store(path)
            self.assertEqual(latest_update(store,CASE),first)
            second=run_update(CASE,QUESTION,Fixture().gateway(),discovered_for(store,CASE),latest_update(store,CASE));save_update(store,second)
            self.assertEqual(len(discovered_for(store,CASE)),1)
            self.assertEqual(second['new_record_ids'],[])
            self.assertEqual(len(store.reviews(second['id'])),0)
            self.assertEqual(store.runs(CASE)[-1],first)
            store.db.close()

    def test_stale_parent_cannot_overwrite_newer_run(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'db');first=run_update(CASE,QUESTION,Fixture().gateway())
            competing=run_update(CASE,QUESTION,Fixture().gateway())
            save_update(store,first)
            with self.assertRaises(ValueError):save_update(store,competing)
            self.assertEqual(len(store.runs(CASE)),1);store.db.close()

    def test_changed_snapshot_hash_blocks_save(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'db');result=run_update(CASE,QUESTION,Fixture().gateway());result['status']='altered'
            with self.assertRaises(ValueError):save_update(store,result)
            self.assertEqual(store.runs(CASE),[]);store.db.close()

    def test_export_contains_discoveries_citations_history_and_reports(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'db');result=run_update(CASE,QUESTION,Fixture().gateway());save_update(store,result)
            from research import initialize_research
            initialize_research(store)
            path=Path(d)/'export.zip';export_bundle(store,CASE,path)
            with zipfile.ZipFile(path) as z:
                self.assertIn('discovered_records.json',z.namelist())
                self.assertIn('search/'+result['id']+'.html',z.namelist())
                self.assertIn('reports/'+result['id']+'.txt',z.namelist())
                for line in z.read('SHA256SUMS.txt').decode().splitlines():
                    digest,name=line.split('  ',1);self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),digest)
            self.assertIn('NOT_REQUESTED',render_update_report(result));store.db.close()

    def test_sources_page_escapes_model_text_and_blocks_active_content(self):
        raw=search_raw('<script>alert(1)</script>')
        discovery={'result':parse_grounding(raw,CASE,'2026-10-30T12:00:00Z')}
        page=search_document(discovery)
        self.assertIn('&lt;script&gt;',page)
        self.assertIn('Content-Security-Policy',page)
        self.assertIn('Provider search suggestions fixture',page)

if __name__=='__main__':unittest.main()
