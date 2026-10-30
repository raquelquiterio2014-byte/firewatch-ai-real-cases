"""Offline Windows widget/persistence check; no real provider calls."""
import json
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

from core import Store
from main import App
from updates import UpdateGateway, run_update, save_update

def transport(url,payload,key,timeout):
    if 'tools' in payload:
        claim='Synthetic GUI fixture research statement.'
        return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':claim}]},
            'groundingMetadata':{'webSearchQueries':['synthetic GUI fixture'],
                'groundingChunks':[{'web':{'uri':'https://example.org/gui-fixture','title':'GUI fixture'}}],
                'groundingSupports':[{'segment':{'text':claim},'groundingChunkIndices':[0]}]}}]}
    data=json.loads(payload['contents'][0]['parts'][0]['text']);record=data['records'][0]
    output=dict(needs_review=False,summary='Synthetic GUI fixture only.',
        findings=[dict(evidence_id=record['id'],excerpt=record['claim'],interpretation='Synthetic interpretation.')],
        issues=[],resolutions=[],gaps=[])
    return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(output)}]}}]}

def main():
    def fail(*args,**kwargs):raise AssertionError('Unexpected UI dialog: '+str(args))
    with tempfile.TemporaryDirectory() as d, patch('main.Store',side_effect=lambda:Store(Path(d)/'db')), patch('main.messagebox.showerror',side_effect=fail), patch('main.messagebox.showinfo',side_effect=fail):
        root=tk.Tk();root.withdraw()
        try:
            app=App(root)
            assert app.tabs.select()==str(app.updates_tab)
            result=run_update(app.case['id'],'Synthetic GUI fixture',UpdateGateway('fixture-key-987654321',transport=transport))
            save_update(app.store,result);app.show_latest_update();app.refresh_history()
            app.history.set(result['id']);app.select_run()
            assert app.current_update['id']==result['id']
            assert 'NOT_REQUESTED' in app.update_summary.get()
            assert 'Synthetic GUI fixture' in app.update_text.get('1.0','end')
            app.choice.current(0);app.load()
            assert app.current_update is None
            app.choice.current(7);app.load()
            assert app.current_update['id']==result['id']
            for size in ('820x600','1120x760'):
                root.geometry(size);root.update_idletasks()
            print('Web-update widgets, case isolation and saved recommendations: OK (offline fixture)')
        finally:
            app.store.db.close();root.destroy()

if __name__=='__main__':main()
