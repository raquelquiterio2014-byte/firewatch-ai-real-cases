import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core import analyze
from gemini_gateway import GeminiGateway, RequestFailed, validate_output, OutputInvalid, load_key, post_json

KEY='fixture-secret-not-a-real-api-key-987654321'

def evidence():return dict(id='e1',case_id='FW-RC-001',claim='Synthetic fixture reports smoke.',source_url='https://example.org/not-real-evidence',locator='test only',observed_at='2018-11-08T12:00:00Z',available_at='2018-11-08T12:30:00Z',verification_note='fixture',reviewer='Synthetic researcher',topic='fire',source_role='contemporaneous_record',verified=True,conflict=False)

def output():return {'findings':[{'evidence_id':'e1','excerpt':'reports smoke','interpretation':'This reported observation needs corroboration.'}],'gaps':['Local access evidence is missing.'],'cautions':['No operational conclusion can be drawn.'],'needs_review':True}

def response(obj=None):return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(obj if obj is not None else output())}]}}],'modelVersion':'gemini-2.5-flash','usageMetadata':{'totalTokenCount':100}}

class GeminiTests(unittest.TestCase):
    def call(self,transport,key=KEY):return GeminiGateway(key,transport=transport,sleep=lambda _:None).call('evidence','2018-11-08T13:00:00Z',[evidence()])
    def test_success_and_secret_absent(self):
        seen=[]
        def transport(url,payload,key,timeout):
            seen.append((url,payload,key));return response()
        r=self.call(transport)
        self.assertEqual(r['source'],'gemini');self.assertEqual(r['attempts'],1);self.assertNotIn(KEY,json.dumps(r))
        self.assertNotIn(KEY,seen[0][0]);self.assertEqual(seen[0][2],KEY)
    def test_prompt_excludes_identity_url_and_catalogue(self):
        seen=[]
        r=self.call(lambda u,p,k,t:(seen.append(json.dumps(p)) or response()))
        for secret in ['Synthetic researcher','example.org','verification_note','Camp Fire','NIST']:
            self.assertNotIn(secret,seen[0])
        self.assertEqual(r['reason'],'OK')
    def test_missing_key_no_request(self):
        r=self.call(lambda *a:self.fail('Network used'),key='');self.assertEqual(r['reason'],'MISSING_KEY');self.assertEqual(r['attempts'],0)
    def test_empty_evidence_no_request(self):
        r=GeminiGateway(KEY,transport=lambda *a:self.fail('Network used')).call('evidence','',[]);self.assertEqual(r['reason'],'NO_ADMITTED_EVIDENCE')
    def test_unknown_citation_rejected(self):
        o=output();o['findings'][0]['evidence_id']='future-source'
        r=self.call(lambda *a:response(o));self.assertEqual(r['reason'],'INVALID_STRUCTURED_OUTPUT');self.assertEqual(r['attempts'],3)
    def test_fabricated_excerpt_rejected(self):
        o=output();o['findings'][0]['excerpt']='There was no fire'
        with self.assertRaises(OutputInvalid):validate_output(o,[evidence()])
    def test_gate_cannot_be_disabled(self):
        o=output();o['needs_review']=False
        with self.assertRaises(OutputInvalid):validate_output(o,[evidence()])
    def test_transient_retry_success(self):
        calls=[];delays=[]
        def transport(*args):
            calls.append(1)
            if len(calls)<3:raise RequestFailed('HTTP_429',True)
            return response()
        r=GeminiGateway(KEY,transport=transport,sleep=delays.append).call('evidence','',[evidence()])
        self.assertEqual(r['source'],'gemini');self.assertEqual(delays,[1,2]);self.assertEqual(r['attempts'],3)
    def test_auth_error_not_retried(self):
        def transport(*args):raise RequestFailed('HTTP_403')
        r=self.call(transport);self.assertEqual(r['attempts'],1);self.assertEqual(r['reason'],'HTTP_403')
    def test_network_bounded_fallback(self):
        def transport(*args):raise RequestFailed('NETWORK_ERROR',True)
        r=self.call(transport);self.assertEqual(r['attempts'],3);self.assertEqual(r['source'],'deterministic_fallback')
    def test_malformed_json_rejected(self):
        r=self.call(lambda *a:{'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'oops'}]}}]});self.assertEqual(r['reason'],'INVALID_STRUCTURED_OUTPUT')
    def test_incomplete_output_rejected(self):
        r=response();r['candidates'][0]['finishReason']='MAX_TOKENS'
        self.assertEqual(self.call(lambda *a:r)['reason'],'INCOMPLETE_OR_BLOCKED')
    def test_prompt_cutoff_integration_and_dependent_critic(self):
        prompts=[]
        def transport(u,p,k,t):prompts.append(json.loads(p['contents'][0]['parts'][0]['text']));return response()
        late=dict(evidence(),id='late',claim='SECRET FUTURE OUTCOME',available_at='2020-01-01T00:00:00Z')
        r=analyze('FW-RC-001','2018-11-08T13:00:00Z',[evidence(),late],GeminiGateway(KEY,transport=transport))
        self.assertEqual(len(prompts),2);self.assertEqual(prompts[1]['previous_analysis'],output())
        self.assertNotIn('SECRET FUTURE OUTCOME',json.dumps(prompts));self.assertEqual(r['mode'],'llm_assisted');self.assertEqual(r['status'],'PARTIAL_DOSSIER')
        self.assertEqual(len(r['trace']),10);self.assertEqual(r['severity'],'NOT_ESTIMATED');self.assertEqual(r['human_review'],'PENDING')
    def test_failed_llm_does_not_unblock(self):
        r=analyze('FW-RC-001','2018-11-08T13:00:00Z',[],GeminiGateway(KEY,transport=lambda *a:self.fail('network')))
        self.assertEqual(r['status'],'BLOCKED_NO_ADMISSIBLE_EVIDENCE');self.assertEqual(r['mode'],'deterministic_fallback')
    def test_probe_no_case_content(self):
        seen=[];o={'findings':[],'gaps':[],'cautions':[],'needs_review':True}
        r=GeminiGateway(KEY,transport=lambda u,p,k,t:(seen.append(p) or response(o))).probe()
        self.assertEqual(r['source'],'gemini');self.assertEqual(json.loads(seen[0]['contents'][0]['parts'][0]['text'])['admitted_claims'],[])
    def test_key_environment_precedence(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'.env').write_text('GEMINI_API_KEY="local-test-key"\n')
            with patch.dict(os.environ,{'GEMINI_API_KEY':'environment-test-key'}):self.assertEqual(load_key(d),'environment-test-key')
            with patch.dict(os.environ,{'GEMINI_API_KEY':''}):self.assertEqual(load_key(d),'local-test-key')
    def test_invalid_model_blocks_url_injection(self):
        r=GeminiGateway(KEY,model='https://evil.example/',transport=lambda *a:self.fail('network')).probe();self.assertEqual(r['reason'],'INVALID_MODEL_NAME')
    def test_secret_echo_dropped(self):
        o=output();o['gaps']=[KEY]
        r=self.call(lambda *a:response(o));self.assertEqual(r['source'],'deterministic_fallback');self.assertNotIn(KEY,json.dumps(r))
    def test_unexpected_error_redacted(self):
        def transport(*args):raise RuntimeError(KEY)
        r=self.call(transport);self.assertNotIn(KEY,json.dumps(r));self.assertEqual(r['reason'],'UNEXPECTED_GATEWAY_ERROR')
    def test_oversized_input_no_request(self):
        e=dict(evidence(),claim='x'*61000)
        r=GeminiGateway(KEY,transport=lambda *a:self.fail('network')).call('evidence','',[e]);self.assertEqual(r['reason'],'INPUT_TOO_LARGE')
    def test_actual_http_request_contract(self):
        class FakeResponse:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return json.dumps(response()).encode()
        with patch('gemini_gateway.request.build_opener') as builder:
            builder.return_value.open.return_value=FakeResponse()
            result=post_json('https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent',{'contents':[]},KEY,25)
            req=builder.return_value.open.call_args.args[0]
            self.assertEqual(req.get_method(),'POST');self.assertEqual(req.get_header('X-goog-api-key'),KEY);self.assertEqual(result,response())

if __name__=='__main__':unittest.main()
