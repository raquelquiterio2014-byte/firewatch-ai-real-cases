"""Cutoff-aware research workflow with optional Gemini; no operational fire-risk model."""
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent

def now():
    return datetime.now(timezone.utc).isoformat()

def timestamp(value):
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        raise ValueError('Use ISO 8601: 2018-11-08T15:00:00Z') from None
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('Timestamp must include UTC Z or an explicit offset.')
    return dt.astimezone(timezone.utc)

def catalogue():
    return json.loads((ROOT / 'data/catalogue.json').read_text(encoding='utf-8'))

def validate_evidence(e):
    required = ('case_id','claim','source_url','locator','observed_at','available_at','verification_note','reviewer','topic')
    for key in required:
        if not isinstance(e.get(key),str) or not e[key].strip():
            raise ValueError(f'Missing {key}')
    if e['case_id'] not in {c['id'] for c in catalogue()}:
        raise ValueError('Unknown case')
    url = urlparse(e['source_url'])
    if url.scheme != 'https' or not url.netloc:
        raise ValueError('Source URL must be an HTTPS address.')
    if timestamp(e['observed_at']) > timestamp(e['available_at']):
        raise ValueError('Observation cannot be later than source availability.')
    if e.get('source_role') != 'contemporaneous_record':
        raise ValueError('Admission requires an original contemporaneous record; retrospective research belongs in the catalogue.')
    if e['topic'] not in ('fire','weather','access','exposure','other'):
        raise ValueError('Invalid topic')
    if type(e.get('verified')) is not bool or type(e.get('conflict')) is not bool:
        raise ValueError('Verification/conflict flags must be boolean.')
    return e

class Store:
    def __init__(self, path=None):
        target = Path(path) if path else ROOT / 'workspace/firewatch.sqlite3'
        target.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(target)
        self.db.execute('CREATE TABLE IF NOT EXISTS evidence (id TEXT PRIMARY KEY, case_id TEXT NOT NULL, payload TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, case_id TEXT NOT NULL, payload TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, run_id TEXT NOT NULL, payload TEXT NOT NULL)')
        self.db.commit()
    def add_evidence(self,e):
        validate_evidence(e)
        e = dict(e,id=str(uuid.uuid4()),registered_at=now())
        self.db.execute('INSERT INTO evidence VALUES (?,?,?)',(e['id'],e['case_id'],json.dumps(e,ensure_ascii=False)))
        self.db.commit()
        return e
    def evidence(self,case_id):
        return [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM evidence WHERE case_id=? ORDER BY rowid',(case_id,))]
    def save_run(self,r):
        self.db.execute('INSERT INTO runs VALUES (?,?,?)',(r['id'],r['case_id'],json.dumps(r,ensure_ascii=False)))
        self.db.commit()
    def runs(self,case_id):
        return [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM runs WHERE case_id=? ORDER BY rowid DESC',(case_id,))]
    def review(self,run_id,reviewer,decision,note):
        saved=self.db.execute('SELECT payload FROM runs WHERE id=?',(run_id,)).fetchone()
        if not saved:
            raise ValueError('Unknown run')
        if json.loads(saved[0]).get('analysis_mode')=='bounded_source_product_review':
            raise ValueError('Pilot runs require the dedicated source/temporal research checklist.')
        if not reviewer.strip() or not note.strip() or decision not in ('ACCEPT_RESEARCH_RECORD','REQUEST_CORRECTION'):
            raise ValueError('Reviewer, decision and rationale are required.')
        r = dict(id=str(uuid.uuid4()),run_id=run_id,reviewer=reviewer,decision=decision,note=note,recorded_at=now(),scope='Research record only; no operational approval')
        self.db.execute('INSERT INTO reviews VALUES (?,?,?)',(r['id'],run_id,json.dumps(r,ensure_ascii=False)))
        self.db.commit()
        return r
    def reviews(self,run_id):
        return [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM reviews WHERE run_id=? ORDER BY rowid',(run_id,))]

def analyze(case_id,cutoff,evidence,gateway=None):
    """Dependent deterministic steps assess dossier readiness; no severity inference."""
    cut=timestamp(cutoff)
    if case_id not in {c['id'] for c in catalogue()}:
        raise ValueError('Unknown case')
    trace=[]
    def step(agent,inputs,output):
        trace.append(dict(sequence=len(trace)+1,agent=agent,at=now(),inputs=inputs,output=output))
        return output
    plan=step('Planner',{'case_id':case_id,'cutoff':cut.isoformat()}, {'required_topics':['fire','weather','access','exposure'],'mode':'deterministic_research_readiness'})
    admitted=[]; excluded=[]
    for e in evidence:
        reason=None
        try:
            validate_evidence(e)
            if e['case_id'] != case_id: reason='WRONG_CASE'
            elif not e['verified']: reason='UNVERIFIED'
            elif timestamp(e['available_at'])>cut or timestamp(e['observed_at'])>cut: reason='AFTER_CUTOFF'
        except ValueError as exc:
            reason=f'INVALID: {exc}'
        if reason: excluded.append({'id':e.get('id'),'reason':reason})
        else: admitted.append(e)
    ev=step('Evidence',plan,{'admitted_ids':[e['id'] for e in admitted],'excluded':excluded})
    llm_evidence=None; llm_critic=None
    if gateway is not None:
        llm_evidence=step('Gemini Evidence',ev,gateway.call('evidence',cut.isoformat(),admitted))
    impact=step('Risk / Impact',{'evidence':ev,'llm_evidence':llm_evidence},{'observations':[{'evidence_id':e['id'],'topic':e['topic'],'claim':e['claim']} for e in admitted],'severity':'NOT_ESTIMATED'})
    missing=sorted(set(plan['required_topics'])-{e['topic'] for e in admitted})
    decision=step('Decision',impact,{'status':'BLOCKED_NO_ADMISSIBLE_EVIDENCE' if not admitted else 'PARTIAL_DOSSIER' if missing else 'READY_FOR_HUMAN_RESEARCH_REVIEW','missing_topics':missing})
    conflicts=[e['id'] for e in admitted if e['conflict']]
    critic=step('Critic',decision,{'conflict_ids':conflicts,'status':'UNRESOLVED_CONFLICT' if conflicts else 'NO_MANUALLY_FLAGGED_CONFLICTS','limitation':'No automatic semantic contradiction detection.'})
    if gateway is not None:
        previous=llm_evidence['output'] if llm_evidence and llm_evidence['source']=='gemini' else None
        llm_critic=step('Gemini Critic',{'critic':critic,'llm_evidence':llm_evidence},gateway.call('critic',cut.isoformat(),admitted,previous))
    safe=step('Safety',{'decision':decision,'critic':critic,'llm_critic':llm_critic},{'operational_use':False,'human_review_required':True,'status':'HOLD_CONFLICT' if conflicts else decision['status']})
    gate=step('Human Gate',safe,{'status':'PENDING','authority':'Research review only'})
    step('Reporter',{'safety':safe,'gate':gate},{'status':safe['status'],'evidence_count':len(admitted)})
    payload=dict(id=str(uuid.uuid4()),case_id=case_id,created_at=now(),cutoff=cut.isoformat(),mode='deterministic_research_readiness',status=safe['status'],severity='NOT_ESTIMATED',missing_topics=missing,admitted_evidence=admitted,excluded_evidence=excluded,trace=trace,human_review='PENDING',limitations=['Sources and availability attested by the registering researcher; no automatic authenticity verification.','No fire prediction, spread model, causal attribution or historical outcome validation.','Gemini 2.5 Flash and LangGraph are planned integrations; not active in v0.1.'])
    payload['llm']={'requested':gateway is not None,'evidence':llm_evidence,'critic':llm_critic}
    if gateway is not None:
        sources=[x['source'] for x in (llm_evidence,llm_critic)]
        payload['mode']='llm_assisted' if all(x=='gemini' for x in sources) else 'llm_partial_fallback' if 'gemini' in sources else 'deterministic_fallback'
    payload['limitations'][-1]='Gemini interpretations require human semantic review. LangGraph orchestration remains planned.'
    payload['content_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return payload

def export_bundle(store,case_id,destination):
    import csv
    import io
    import zipfile
    case=next(c for c in catalogue() if c['id']==case_id)
    runs=store.runs(case_id)
    files={}
    for name,obj in [('dossier.json',case),('evidence.json',store.evidence(case_id)),('runs.json',runs),('reviews.json',[r for run in runs for r in store.reviews(run['id'])])]:
        files[name]=json.dumps(obj,ensure_ascii=False,indent=2).encode('utf-8')
    if store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='research_evidence'").fetchone():
        from research import evidence_for, render_report
        files['research_evidence.json']=json.dumps(evidence_for(store,case_id),ensure_ascii=False,indent=2).encode('utf-8')
        for r in runs:files['reports/'+r['id']+'.txt']=render_report(r).encode('utf-8')
    if case_id=='FW-RC-008' and (ROOT/'data/curated_pilot.json').exists():
        from pilot import dataset as pilot_dataset, artifact_path
        for name in ['curated_pilot.json','pilot_technical_review.json']:
            files['pilot/'+name]=(ROOT/'data'/name).read_bytes()
        for product in pilot_dataset()['products']:
            path=artifact_path(product)
            if path.is_file():files[product['file']]=path.read_bytes()
        files['originals/ATTRIBUTION.txt']=(ROOT/'originals/ATTRIBUTION.txt').read_bytes()
    if store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='discovered_records'").fetchone():
        from updates import discovered_for, search_document
        files['discovered_records.json']=json.dumps(discovered_for(store,case_id),ensure_ascii=False,indent=2).encode('utf-8')
        for r in runs:
            if r.get('analysis_mode')=='dynamic_research_update':
                files['search/'+r['id']+'.html']=search_document(r['discovery']).encode('utf-8')
    files['trace.jsonl']=''.join(json.dumps(dict(run_id=r['id'],**t),ensure_ascii=False)+'\n' for r in runs for t in r['trace']).encode('utf-8')
    stream=io.StringIO(newline=''); fields=['id','publisher','title','url','role','reviewed_on']
    writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore'); writer.writeheader();writer.writerows(case['sources'])
    files['sources.csv']=stream.getvalue().encode('utf-8-sig')
    files['README.txt']=b'Research dossier. Catalogue sources are research-only, not automatically admitted evidence. Reviews are linked to immutable run IDs. No operational recommendations. Local SHA-256 checksums detect modification; they do not establish source authenticity.\n'
    files['SHA256SUMS.txt']=''.join(hashlib.sha256(content).hexdigest()+'  '+name+'\n' for name,content in files.items()).encode()
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
        for name,content in files.items():z.writestr(name,content)
