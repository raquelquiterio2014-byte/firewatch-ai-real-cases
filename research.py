"""Prefilled, source-attributed document analysis, distinct from responder-time replay."""
import hashlib
import json
import uuid
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from core import ROOT, catalogue, now

DATASET_VERSION='2026-10-17-v1'

def research_seed():return json.loads((ROOT/'data/research_evidence.json').read_text(encoding='utf-8'))

def validate_research(e):
    for field in ('id','case_id','claim','topic','source_url','source_title','publisher','locator','source_anchor','event_period','curation_method'):
        if not isinstance(e.get(field),str) or not e[field].strip():raise ValueError('Missing research field: '+field)
    if e['case_id'] not in {c['id'] for c in catalogue()}:raise ValueError('Unknown case')
    if e.get('source_role')!='retrospective_documented':raise ValueError('Wrong research evidence role')
    if e.get('content_checked') is not True:raise ValueError('Web content not checked')
    if e.get('original_availability_verified') is not False:raise ValueError('Research seed cannot assert original responder availability')
    if e.get('observed_at') is not None or e.get('available_at') is not None:raise ValueError('Use event_period and date-level source metadata; do not invent exact times')
    if e['topic'] not in ('fire','weather','access','exposure','other'):raise ValueError('Invalid topic')
    if urlparse(e['source_url']).scheme!='https' or not urlparse(e['source_url']).netloc:raise ValueError('Invalid source URL')
    checked=date.fromisoformat(e['content_checked_on'])
    if e.get('source_published_on') and date.fromisoformat(e['source_published_on'])>checked:raise ValueError('Publication after content check')
    return e

def initialize_research(store):
    records=research_seed()
    for e in records:validate_research(e)
    store.db.execute('CREATE TABLE IF NOT EXISTS research_evidence (id TEXT PRIMARY KEY, case_id TEXT NOT NULL, payload TEXT NOT NULL)')
    with store.db:
        for e in records:store.db.execute('INSERT OR IGNORE INTO research_evidence VALUES (?,?,?)',(e['id'],e['case_id'],json.dumps(e,ensure_ascii=False)))
    return len(records)

def evidence_for(store,case_id):
    return [json.loads(r[0]) for r in store.db.execute('SELECT payload FROM research_evidence WHERE case_id=? ORDER BY id',(case_id,))]

def analyze_research(case_id,evidence,gateway=None,as_of='2026-10-17'):
    review_date=date.fromisoformat(as_of)
    case=next((c for c in catalogue() if c['id']==case_id),None)
    if case is None:raise ValueError('Unknown case')
    trace=[]
    def step(agent,inputs,output):
        trace.append(dict(sequence=len(trace)+1,agent=agent,at=now(),inputs=inputs,output=output));return output
    plan=step('Planner',{'case_id':case_id,'as_of':as_of},{'analysis_mode':'retrospective_document_analysis','task':'Summarize documented observations and identify research gaps. Later reconstructions permitted; no responder-time replay.'})
    admitted=[];excluded=[]
    for e in evidence:
        reason=None
        try:
            validate_research(e)
            if e['case_id']!=case_id:reason='WRONG_CASE'
            elif date.fromisoformat(e['content_checked_on'])>review_date:reason='CHECKED_AFTER_REVIEW_DATE'
        except (ValueError,TypeError) as exc:reason='INVALID_RESEARCH_RECORD: '+str(exc)
        if reason:excluded.append({'id':e.get('id'),'reason':reason})
        else:admitted.append(e)
    ids=[e['id'] for e in admitted]
    ev=step('Evidence',plan,{'admitted_ids':ids,'excluded':excluded,'verification_scope':'Institutional webpage content checked; underlying raw data not independently authenticated.'})
    llm_evidence=None;llm_critic=None
    if gateway is not None:llm_evidence=step('Gemini Evidence',ev,gateway.call('evidence',as_of,admitted,analysis_mode='retrospective_document_analysis'))
    topics=sorted({e['topic'] for e in admitted})
    counts=Counter(e['source_url'] for e in admitted)
    missing=sorted({'fire','weather','access','exposure'}-set(topics))
    impact=step('Risk / Impact',{'evidence':ev,'llm_evidence':llm_evidence},{'documented_topics':topics,'missing_context_topics':missing,'source_count':len(counts),'record_count':len(admitted),'severity':'NOT_ESTIMATED','note':'Multiple claims from one publication are not independent corroboration.'})
    decision=step('Decision',impact,{'status':'RETROSPECTIVE_DOCUMENT_ANALYSIS_COMPLETED' if admitted else 'BLOCKED_NO_RESEARCH_EVIDENCE','research_actions':['Review missing context and original records.','Check source interpretation and spatial scope.','Seek independent corroboration before evaluating decisions.']})
    critic=step('Critic',decision,{'manually_flagged_conflicts':[e['id'] for e in admitted if e.get('conflict')],'concerns':['No verified responder-time information set.','Date-level publication metadata must not become an exact availability timestamp.','Document analysis completion is not historical model validation.']})
    if gateway is not None:
        previous=llm_evidence['output'] if llm_evidence['source']=='gemini' else None
        llm_critic=step('Gemini Critic',{'critic':critic,'llm_evidence':llm_evidence},gateway.call('critic',as_of,admitted,previous,analysis_mode='retrospective_document_analysis'))
    safe=step('Safety',{'decision':decision,'critic':critic,'llm_critic':llm_critic},{'operational_use':False,'human_review_required':True,'status':'HOLD_CONFLICT' if critic['manually_flagged_conflicts'] else decision['status']})
    step('Human Gate',safe,{'status':'PENDING','authority':'Document interpretation review only'})
    report={'case_name':case['name'],'analysis_mode':'retrospective_document_analysis','supported_findings':[{'evidence_id':e['id'],'claim':e['claim'],'source_url':e['source_url'],'locator':e['locator']} for e in admitted],'context':impact,'next_steps':decision['research_actions']}
    step('Reporter',safe,{'status':safe['status'],'finding_ids':ids})
    mode='deterministic_document_analysis'
    if gateway is not None:
        sources=[llm_evidence['source'],llm_critic['source']]
        mode='llm_assisted' if all(x=='gemini' for x in sources) else 'llm_partial_fallback' if 'gemini' in sources else 'deterministic_fallback'
    payload=dict(id=str(uuid.uuid4()),case_id=case_id,created_at=now(),cutoff=None,review_as_of=as_of,analysis_mode='retrospective_document_analysis',mode=mode,status=safe['status'],severity='NOT_ESTIMATED',missing_topics=missing,admitted_evidence=admitted,excluded_evidence=excluded,trace=trace,human_review='PENDING',report=report,llm={'requested':gateway is not None,'evidence':llm_evidence,'critic':llm_critic},dataset_version=DATASET_VERSION,limitations=critic['concerns'])
    payload['content_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return payload

def render_report(r):
    lines=[f"FIREWATCH AI — {r.get('report',{}).get('case_name',r['case_id'])}",f"Analysis: {r.get('analysis_mode','historical_cutoff')}",f"Engine: {r['mode']}",f"Status: {r['status']}",f"Run: {r['id']}",'Human research review: PENDING in original run; see linked reviews.','']
    if r.get('analysis_mode')=='bounded_source_product_review':
        lines += ['PILOT CUTOFF: '+r['cutoff'],'Technical source review: AI assistant; independent human approval remains pending.','Strict responder-time replay eligible: FALSE','']
        for decision in r['product_decisions']:
            lines += [decision['product_id']+' | '+decision['reason'],'Methodological interval: '+decision['bounds']['lower']+' to '+decision['bounds']['upper']]
        lines += ['']
    if 'report' in r:
        ctx=r['report']['context'];lines+=['DOCUMENTED FINDINGS']
        for f in r['report']['supported_findings']:lines += [f"[{f['evidence_id']}] {f['claim']}",f"Source: {f['source_url']}",f"Locator: {f['locator']}",'']
        lines += [f"Independent source documents: {ctx['source_count']}",f"Missing context topics: {', '.join(ctx['missing_context_topics']) or 'None in topic checklist; sufficiency still unproven.'}",'','RESEARCH NEXT STEPS']+r['report']['next_steps']
    else:lines += ['Admitted original records: '+str(len(r['admitted_evidence'])),'Missing topics: '+', '.join(r['missing_topics'])]
    for role in ('evidence','critic'):
        result=r.get('llm',{}).get(role)
        if result:
            lines+=['',f"GEMINI {role.upper()}: {result['source']} / {result['reason']}"]
            if result.get('output'):
                out=result['output']
                for f in out['findings']:lines += [f"[{f['evidence_id']}] Model interpretation (unvalidated): {f['interpretation']}",f"Quoted registered claim: {f['excerpt']}"]
                lines+=['Gaps:']+out['gaps']+['Cautions:']+out['cautions']
    return '\n'.join(lines+['','LIMITATIONS']+r['limitations'])

def run_batch(cases,evidence_map,gateway=None,progress=None):
    """Sequential calls. Stop further external calls after persistent quota/auth failures."""
    results=[];halt_reason=None
    class Halted:
        def call(self,*args,**kwargs):return {'source':'deterministic_fallback','reason':'BATCH_API_PAUSED_'+halt_reason,'attempts':0,'attempt_log':[],'output':None}
    for n,c in enumerate(cases,1):
        active=Halted() if halt_reason else gateway
        r=analyze_research(c['id'],evidence_map[c['id']],active)
        results.append(r)
        if gateway and not halt_reason:
            for role in ('evidence','critic'):
                reason=r['llm'][role]['reason']
                if reason in ('MISSING_KEY','HTTP_401','HTTP_403','HTTP_404','HTTP_429'):
                    halt_reason=reason;break
        if progress:progress(n,len(cases),r)
    return results

def export_all_cases(store,destination):
    import tempfile
    import zipfile
    from core import export_bundle
    with tempfile.TemporaryDirectory() as directory:
        files={}
        for case in catalogue():
            path=Path(directory)/(case['id']+'.zip');export_bundle(store,case['id'],path);files[path.name]=path.read_bytes()
        summary=[{'case_id':c['id'],'records':len(evidence_for(store,c['id'])),'runs':len(store.runs(c['id']))} for c in catalogue()]
        files['summary.json']=json.dumps(summary,indent=2).encode()
        files['README.txt']=b'Ten retrospective document dossiers. Analysis completion is not model accuracy or validated historical decision support. Inner bundles contain reports, evidence provenance, reviews, traces and checksums.\n'
        files['SHA256SUMS.txt']=''.join(hashlib.sha256(v).hexdigest()+'  '+k+'\n' for k,v in files.items()).encode()
        with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
            for name,value in files.items():z.writestr(name,value)
