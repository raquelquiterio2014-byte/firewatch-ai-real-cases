"""Run the curated source-product pilot. Offline by default."""
import argparse
from core import Store,export_bundle
from pilot import dataset,analyze_pilot,initialize_pilot
from research import initialize_research,render_report
from gemini_gateway import GeminiGateway,load_key

def main():
 p=argparse.ArgumentParser();p.add_argument('--checkpoint',choices=['EARLY','PRIMARY','LATER'],default='PRIMARY');p.add_argument('--strict',action='store_true');p.add_argument('--gemini',action='store_true');p.add_argument('--output',default='FireWatch_First_Curated_Dossier.zip');a=p.parse_args()
 cutoff=next(c['cutoff'] for c in dataset()['checkpoints'] if c['id']==a.checkpoint)
 store=Store();initialize_research(store);initialize_pilot(store)
 r=analyze_pilot(cutoff,GeminiGateway(load_key()) if a.gemini else None,strict=a.strict)
 store.save_run(r);export_bundle(store,'FW-RC-008',a.output);store.db.close()
 print(render_report(r));print('\nExport:',a.output)
if __name__=='__main__':main()
