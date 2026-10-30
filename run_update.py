"""Explicit fresh search; no periodic scheduling or hidden provider requests."""
import argparse
import json
from pathlib import Path
from core import Store
from gemini_gateway import MODEL, load_key
from updates import UpdateGateway, discovered_for, latest_update, run_update, save_update, render_update_report

def main():
    parser=argparse.ArgumentParser(description='FireWatch web discovery and research-intervention reassessment')
    parser.add_argument('--case',default='FW-RC-008')
    parser.add_argument('--question',default='Find newly available publications, corrections and evidence about this historical case. What needs human research attention now?')
    parser.add_argument('--model',default=MODEL)
    parser.add_argument('--db',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--txt',type=Path)
    args=parser.parse_args()
    store=Store(args.db)
    try:
        result=run_update(args.case,args.question,UpdateGateway(load_key(),args.model),
                          discovered_for(store,args.case),latest_update(store,args.case))
        save_update(store,result)
        for path,content in ((args.output,json.dumps(result,indent=2,ensure_ascii=False)),(args.txt,render_update_report(result))):
            if path:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(content+'\n',encoding='utf-8',newline='')
        print(json.dumps(dict(run_id=result['id'],mode=result['mode'],
                              new_records=len(result['new_record_ids']),review=result['review_assessment']),indent=2))
        return 0 if result['mode']=='llm_assisted' else 2
    finally:
        store.db.close()

if __name__=='__main__':
    raise SystemExit(main())
