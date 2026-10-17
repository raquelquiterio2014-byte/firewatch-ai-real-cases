"""Run ten prefilled document dossiers. Default: offline. --gemini opts into API calls."""
import argparse
from pathlib import Path
from core import Store, catalogue
from research import initialize_research, evidence_for, run_batch, export_all_cases
from gemini_gateway import GeminiGateway, load_key

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--gemini',action='store_true');parser.add_argument('--output',default='FireWatch_All_10_Cases.zip');args=parser.parse_args()
    store=Store();initialize_research(store)
    cases=catalogue();records={c['id']:evidence_for(store,c['id']) for c in cases}
    gateway=GeminiGateway(load_key()) if args.gemini else None
    def progress(n,total,r):
        store.save_run(r);print(f"{n}/{total} {r['case_id']} {r['status']} {r['mode']}")
    run_batch(cases,records,gateway,progress)
    export_all_cases(store,args.output);store.db.close();print('Exported:',Path(args.output).resolve())
if __name__=='__main__':main()
