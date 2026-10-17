"""Curated original provider maps with conditional temporal bounds and explicit review identity."""
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from core import ROOT, timestamp, now

CASE_ID='FW-RC-008'

def dataset():return json.loads((ROOT/'data/curated_pilot.json').read_text(encoding='utf-8'))
def technical_review():return json.loads((ROOT/'data/pilot_technical_review.json').read_text(encoding='utf-8'))
def dataset_digest():return hashlib.sha256((ROOT/'data/curated_pilot.json').read_bytes()).hexdigest()

def artifact_path(product,root=None):
    base=Path(root or ROOT).resolve();path=(base/product['file']).resolve()
    if base not in path.parents:raise ValueError('Artifact outside project')
    return path

def verify_artifacts(data=None,root=None):
    results=[]
    for p in (data or dataset())['products']:
        try:
            path=artifact_path(p,root)
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            status='MATCH' if digest==p['sha256'] else 'HASH_MISMATCH'
        except (OSError,ValueError):status='MISSING_OR_INVALID_PATH'
        results.append({'product_id':p['id'],'status':status,'expected_sha256':p['sha256']})
    return results

def availability_bounds(product):
    local=datetime.strptime(product['delivery_local_without_timezone'],'%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    # The stamp is NOT asserted to be UTC: the +00 here is only a calculation origin.
    earliest_delivery=local-timedelta(hours=14)
    latest_delivery=local+timedelta(hours=12)
    production_start=timestamp(product['production_on_utc']+'T00:00:00Z')
    production_end=production_start+timedelta(days=1)
    observation=timestamp(product['observed_at'])
    if observation>production_end:raise ValueError('Observation later than production-day interval')
    lower=max(observation,production_start,earliest_delivery)
    upper=max(production_end,latest_delivery)
    if lower>upper:raise ValueError('Inconsistent temporal bounds')
    return {'lower':lower.isoformat(),'upper':upper.isoformat(),'exact_availability_verified':False,'basis':'BOUNDED_DELIVERY_V1: conservative methodological interval; portal timezone and downloaded-version linkage unverified.'}

def technical_status(data=None):
    review=technical_review();actual=dataset_digest()
    return {'review_id':review['id'],'reviewer_kind':review['reviewer_kind'],'decision':review['decision'],'dataset_matches_review':review['dataset_sha256']==actual,'human_approval':'PENDING'}

def analyze_pilot(cutoff=None,gateway=None,data=None,root=None,strict=False):
    d=data or dataset();cutoff=cutoff or next(c['cutoff'] for c in d['checkpoints'] if c['id']=='PRIMARY');cut=timestamp(cutoff)
    checks=verify_artifacts(d,root);integrity={c['product_id']:c['status'] for c in checks}
    review=technical_status();review_valid=review['dataset_matches_review'] and (data is None or d==dataset())
    trace=[]
    def step(agent,inputs,out):trace.append({'sequence':len(trace)+1,'agent':agent,'at':now(),'inputs':inputs,'output':out});return out
    plan=step('Planner',{'cutoff':cut.isoformat()},{'task':'Inspect original provider maps available under a conservative bounded-time research assumption.','scope':d['scope'],'strict_mode':strict})
    decisions=[];products={p['id']:p for p in d['products']}
    for p in d['products']:
        bounds=availability_bounds(p)
        if integrity[p['id']]!='MATCH':reason='ARTIFACT_INTEGRITY_FAILURE';admit=False
        elif not review_valid:reason='TECHNICAL_REVIEW_DATASET_MISMATCH';admit=False
        elif strict:reason='ORIGINAL_AVAILABILITY_NOT_INDEPENDENTLY_VERIFIED';admit=False
        elif cut<timestamp(bounds['lower']):reason='BEFORE_AVAILABILITY_INTERVAL';admit=False
        elif cut<timestamp(bounds['upper']):reason='AVAILABILITY_INTERVAL_CROSSES_CUTOFF';admit=False
        else:reason='CONDITIONALLY_ADMITTED_BY_CONSERVATIVE_BOUND';admit=True
        decisions.append({'product_id':p['id'],'admitted':admit,'reason':reason,'bounds':bounds,'warnings':p.get('warnings',[])})
    eligible={p['product_id'] for p in decisions if p['admitted']}
    admitted=[];excluded=[]
    for row in d['evidence']:
        e=dict(row)
        if e['product_id'] in eligible:
            e['availability_bounds']=next(p['bounds'] for p in decisions if p['product_id']==e['product_id']);admitted.append(e)
        else:excluded.append({'id':e['id'],'product_id':e['product_id'],'reason':next(p['reason'] for p in decisions if p['product_id']==e['product_id'])})
    ev=step('Evidence',plan,{'admitted_ids':[e['id'] for e in admitted],'excluded':excluded,'product_decisions':decisions,'integrity':checks})
    le=None;lc=None
    if gateway is not None:le=step('Gemini Evidence',ev,gateway.call('evidence',cut.isoformat(),admitted,analysis_mode='bounded_source_product_review'))
    impact=step('Risk / Impact',{'evidence':ev,'llm_evidence':le},{'documented_topics':sorted({e['topic'] for e in admitted}),'severity':'NOT_ESTIMATED','limitations':['No road-status or evacuation inference from a map base layer.','No confirmed population occupancy or individual outcomes.','CEMS products are not independent field corroboration.']})
    decision=step('Decision',impact,{'status':'CONDITIONAL_SOURCE_REVIEW_COMPLETED' if admitted else 'BLOCKED_NO_ELIGIBLE_ORIGINAL_PRODUCTS','admission_count':len(admitted),'next_action':'Human review of source interpretation and temporal assumptions.'})
    critic=step('Critic',decision,{'technical_review':review,'concerns':['Delivery timezone unknown.','Historical downloaded-version to delivery linkage not verified.','AOI02 portal delivery and PDF production have different calendar dates.','No actual responder receipt or operational validation established.']})
    if gateway is not None:lc=step('Gemini Critic',{'critic':critic,'llm_evidence':le},gateway.call('critic',cut.isoformat(),admitted,le['output'] if le['source']=='gemini' else None,analysis_mode='bounded_source_product_review'))
    safety=step('Safety',{'decision':decision,'critic':critic,'llm_critic':lc},{'status':decision['status'],'operational_use':False,'human_review_required':True,'strict_replay_eligible':False})
    step('Human Gate',safety,{'status':'PENDING','authority':'Research assumptions and source interpretation only.'})
    findings=[{'evidence_id':e['id'],'claim':e['claim'],'source_url':e['source_url'],'locator':e['locator']} for e in admitted]
    step('Reporter',safety,{'finding_ids':[e['id'] for e in admitted],'withheld_ids':[e['id'] for e in excluded]})
    mode='deterministic_bounded_source_review'
    if gateway is not None:
        sources=[le['source'],lc['source']];mode='llm_assisted' if all(x=='gemini' for x in sources) else 'llm_partial_fallback' if 'gemini' in sources else 'deterministic_fallback'
    r=dict(id=str(uuid.uuid4()),case_id=d['case_id'],created_at=now(),cutoff=cut.isoformat(),analysis_mode='bounded_source_product_review',mode=mode,status=safety['status'],severity='NOT_ESTIMATED',strict_replay_eligible=False,human_review='PENDING',admitted_evidence=admitted,excluded_evidence=excluded,product_decisions=decisions,artifact_checks=checks,dataset_sha256=dataset_digest(),technical_review=review,report={'case_name':'Gironde — original CEMS products pilot','supported_findings':findings,'context':{'source_count':len(eligible),'record_count':len(admitted),'missing_context_topics':sorted({'fire','weather','access','exposure'}-set(impact['documented_topics']))},'next_steps':[decision['next_action']]},llm={'requested':gateway is not None,'evidence':le,'critic':lc},trace=trace,limitations=critic['concerns']+impact['limitations'])
    r['content_sha256']=hashlib.sha256(json.dumps(r,sort_keys=True,ensure_ascii=False).encode()).hexdigest();return r

def initialize_pilot(store):
    path=ROOT/'pilot/first_dossier_run.json'
    if not path.exists():return
    r=json.loads(path.read_text())
    if not store.db.execute('SELECT 1 FROM runs WHERE id=?',(r['id'],)).fetchone():store.save_run(r)

def save_human_review(store,run_id,reviewer,decision,note,checks):
    row=store.db.execute('SELECT payload FROM runs WHERE id=?',(run_id,)).fetchone()
    if not row:raise ValueError('Select a saved run first.')
    run=json.loads(row[0])
    if run.get('analysis_mode')!='bounded_source_product_review':raise ValueError('Select a curated pilot run.')
    if not reviewer.strip() or not note.strip():raise ValueError('Reviewer name and review rationale are required.')
    if decision not in ('ACCEPT_RESEARCH_RECORD','REQUEST_CORRECTION'):raise ValueError('Invalid review decision')
    if decision=='ACCEPT_RESEARCH_RECORD':
        required={'source_files_checked','temporal_assumptions_understood','research_limits_understood'}
        if set(checks)!=required or not all(type(v) is bool and v for v in checks.values()):raise ValueError('Confirm the three research review checks before accepting.')
        if run['dataset_sha256']!=dataset_digest() or not all(c['status']=='MATCH' for c in verify_artifacts()):raise ValueError('Current dossier files differ from the reviewed run. Restore files and run again.')
        if not run['admitted_evidence']:raise ValueError('A blocked run cannot be accepted as a completed source review.')
    r=dict(id=str(uuid.uuid4()),run_id=run_id,reviewer=reviewer,reviewer_kind='HUMAN_RESEARCHER',decision=decision,note=note,checks=checks,recorded_at=now(),run_sha256=run['content_sha256'],scope='Research review only; does not verify responder receipt, alter source metadata, or authorize operations.')
    store.db.execute('INSERT INTO reviews VALUES (?,?,?)',(r['id'],run_id,json.dumps(r,ensure_ascii=False)));store.db.commit();return r
