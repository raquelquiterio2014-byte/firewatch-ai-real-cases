import json
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser
from core import Store, catalogue, analyze, export_bundle
from gemini_gateway import GeminiGateway, MODEL, load_key
from research import initialize_research, evidence_for, analyze_research, render_report, run_batch
from pilot import dataset as pilot_dataset, technical_review, verify_artifacts, availability_bounds, analyze_pilot, initialize_pilot, save_human_review, artifact_path

class App:
    def __init__(self,root):
        self.root=root; self.store=Store(); self.cases=catalogue(); self.current_run=None
        initialize_research(self.store);initialize_pilot(self.store)
        root.title('FireWatch AI — Real Cases | Final research release v0.4')
        self.busy=False;self.jobs=queue.Queue()
        root.geometry('1120x760');root.minsize(820,600)
        style=ttk.Style();style.theme_use('clam')
        style.configure('TFrame',background='#f2f4f5');style.configure('TLabel',background='#f2f4f5')
        style.configure('TButton',padding=6);style.configure('TNotebook.Tab',padding=(6,7))
        header=tk.Frame(root,bg='#182c32');header.pack(fill='x')
        tk.Label(header,text='FireWatch AI — Real Cases',fg='white',bg='#182c32',font=('Segoe UI',21,'bold')).pack(anchor='w',padx=18,pady=(12,0))
        tk.Label(header,text='Sourced dossiers • Retrospective evidence • Human research review',fg='#ffb56b',bg='#182c32',font=('Segoe UI',11)).pack(anchor='w',padx=18,pady=(0,12))
        bar=ttk.Frame(root);bar.pack(fill='x',padx=12,pady=10)
        self.choice=ttk.Combobox(bar,state='readonly',values=[f"{c['id']} | {c['name']} | {c['country']}" for c in self.cases],width=80)
        self.choice.pack(side='left',fill='x',expand=True);self.choice.current(0);self.choice.bind('<<ComboboxSelected>>',lambda e:self.load())
        ttk.Button(bar,text='Export case ZIP',command=self.export).pack(side='left',padx=6)
        self.tabs=ttk.Notebook(root);self.tabs.pack(fill='both',expand=True,padx=12,pady=(0,10))
        self.dossier=self.text_tab('Case dossier');self.sources_tab=ttk.Frame(self.tabs);self.tabs.add(self.sources_tab,text='Sources')
        self.source_list=ttk.Treeview(self.sources_tab,columns=('publisher','title'),show='headings',height=6)
        self.source_list.heading('publisher',text='Publisher');self.source_list.heading('title',text='Research source — select then open')
        self.source_list.column('publisher',width=150,stretch=False);self.source_list.column('title',width=650)
        self.source_list.pack(fill='x',padx=8,pady=8)
        ttk.Button(self.sources_tab,text='Open selected source',command=self.open_source).pack(anchor='w',padx=8)
        self.source_text=self.add_text(self.sources_tab)
        self.prefilled=self.text_tab('Prefilled evidence');self.make_evidence_tab();self.make_gemini_tab();self.make_analysis_tab();self.make_pilot_tab();self.trace=self.text_tab('Agent trace');self.make_review_tab()
        navigation=ttk.Frame(root);navigation.pack(fill='x',padx=12)
        ttk.Label(navigation,text='Open view:').pack(side='left')
        self.view=ttk.Combobox(navigation,state='readonly',values=[self.tabs.tab(t,'text') for t in self.tabs.tabs()],width=28);self.view.pack(side='left',padx=6)
        self.view.bind('<<ComboboxSelected>>',lambda e:self.tabs.select(self.view.current()))
        self.tabs.bind('<<NotebookTabChanged>>',lambda e:self.view.set(self.tabs.tab(self.tabs.select(),'text')))
        self.status=tk.StringVar(value='');ttk.Label(root,textvariable=self.status).pack(fill='x',padx=12,pady=(0,8))
        self.choice.current(7)
        self.load()
        self.tabs.select(self.pilot_tab)
        root.after(100,self.poll_jobs)
    @property
    def case(self):return self.cases[self.choice.current()]
    def add_text(self,parent):
        frame=ttk.Frame(parent);frame.pack(fill='both',expand=True,padx=8,pady=8)
        txt=tk.Text(frame,wrap='word',font=('Consolas',10),padx=12,pady=12,background='white')
        scroll=ttk.Scrollbar(frame,command=txt.yview);txt.configure(yscrollcommand=scroll.set)
        txt.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y');return txt
    def text_tab(self,name):
        frame=ttk.Frame(self.tabs);self.tabs.add(frame,text=name);return self.add_text(frame)
    def show(self,widget,value):
        widget.configure(state='normal');widget.delete('1.0','end');widget.insert('1.0',value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2));widget.configure(state='disabled')
    def load(self):
        c=self.case;self.current_run=None
        self.show(self.dossier,f"{c['name']} — {c['country']}\nPeriod: {c['period']}\nScope: {c['scope']}\nStatus: {c['status']}\n\n{c['summary']}\n\nRESEARCH QUESTION\n{c['research_question']}\n\nUNKNOWNS\n"+'\n'.join('• '+x for x in c['unknowns'])+'\n\nAll 10 cases have 3 prefilled source-attributed research records each. Open Prefilled evidence, then Run analysis. This is historical document analysis, not responder-time replay or validated model evaluation.')
        self.source_list.delete(*self.source_list.get_children())
        for s in c['sources']:self.source_list.insert('', 'end',iid=s['id'],values=(s['publisher'],s['title']))
        self.show(self.source_text,c['sources']);self.refresh_research();self.refresh_evidence();self.show(self.trace,'No run selected.')
        self.show(self.results,'Ready: 3 prefilled research records for this case. Use Run analysis or Analyze all 10 cases. Gemini is optional and can be enabled in Gemini settings. Document mode does not require an event-time cutoff.')
        runs=self.store.runs(c['id']);self.history['values']=[r['id'] for r in runs];self.history.set('')
        self.show(self.review_text,[]);self.cutoff.set('');self.status.set(f"{c['id']} | {len(c['sources'])} research sources | {len(runs)} saved runs | 3 prefilled research records — ready to analyze")
    def open_source(self):
        selected=self.source_list.selection()
        if selected:webbrowser.open(next(s['url'] for s in self.case['sources'] if s['id']==selected[0]))
    def make_evidence_tab(self):
        tab=ttk.Frame(self.tabs);self.tabs.add(tab,text='Add original record')
        ttk.Label(tab,text='Register original contemporaneous records. Timestamps require Z or an explicit UTC offset.').pack(anchor='w',padx=8,pady=6)
        form=ttk.Frame(tab);form.pack(fill='x',padx=8)
        self.fields={}
        for i,(key,label) in enumerate([('claim','Observation / claim'),('source_url','Original record HTTPS URL'),('locator','Page / paragraph / product ID'),('observed_at','Observation time (ISO 8601)'),('available_at','Availability time (ISO 8601)'),('verification_note','How availability and content were checked'),('reviewer','Researcher name')]):
            ttk.Label(form,text=label).grid(row=i,column=0,sticky='w',padx=(0,10),pady=2)
            v=tk.StringVar();ttk.Entry(form,textvariable=v).grid(row=i,column=1,sticky='ew',pady=2);self.fields[key]=v
        form.columnconfigure(1,weight=1)
        row=ttk.Frame(tab);row.pack(fill='x',padx=8,pady=5)
        self.topic=tk.StringVar(value='fire');ttk.Combobox(row,state='readonly',textvariable=self.topic,values=['fire','weather','access','exposure','other'],width=12).pack(side='left')
        self.verified=tk.BooleanVar();self.conflict=tk.BooleanVar()
        ttk.Checkbutton(row,text='Original record + availability verified',variable=self.verified).pack(side='left',padx=8)
        ttk.Checkbutton(row,text='Unresolved conflict',variable=self.conflict).pack(side='left')
        ttk.Button(row,text='Register evidence',command=self.register).pack(side='right')
        self.evidence_text=self.add_text(tab)
    def refresh_evidence(self):self.show(self.evidence_text,self.store.evidence(self.case['id']))
    def register(self):
        try:
            e={k:v.get().strip() for k,v in self.fields.items()}
            e.update(case_id=self.case['id'],source_role='contemporaneous_record',topic=self.topic.get(),verified=self.verified.get(),conflict=self.conflict.get())
            self.store.add_evidence(e);self.refresh_evidence()
            for v in self.fields.values():v.set('')
            self.verified.set(False);self.conflict.set(False)
            self.status.set('Evidence registered. Existing runs retain their original evidence snapshot.')
        except (ValueError,OSError) as exc:messagebox.showerror('Evidence registration',str(exc))
    def refresh_research(self):
        records=evidence_for(self.store,self.case['id'])
        lines=['PREFILLED RETROSPECTIVE EVIDENCE','Webpage content checked; independent human verification pending.','Original availability times are unknown and are not invented.','']
        for e in records:
            lines += [e['id']+' | '+e['topic'].upper(),e['claim'],'Event period: '+e['event_period'],'Publisher: '+e['publisher'],'Source: '+e['source_url'],'Locator: '+e['locator'],'Search this short source anchor: '+e['source_anchor'],'Published on: '+str(e['source_published_on'] or 'UNKNOWN'),'Content checked: '+e['content_checked_on'],'']
        self.show(self.prefilled,'\n'.join(lines))
    def make_analysis_tab(self):
        tab=ttk.Frame(self.tabs);self.tabs.add(tab,text='Analysis');self.analysis_tab=tab
        row=ttk.Frame(tab);row.pack(fill='x',padx=8,pady=6)
        self.analysis_mode=tk.StringVar(value='Retrospective documents (prefilled)')
        self.mode_choice=ttk.Combobox(row,state='readonly',textvariable=self.analysis_mode,values=['Retrospective documents (prefilled)','Historical cutoff (original records)'],width=39)
        self.mode_choice.pack(side='left');self.mode_choice.bind('<<ComboboxSelected>>',lambda e:self.set_mode())
        self.run_button=ttk.Button(row,text='Run analysis',command=self.run);self.run_button.pack(side='left',padx=8)
        self.batch_button=ttk.Button(row,text='Analyze all 10 cases',command=self.run_all);self.batch_button.pack(side='left')
        self.export_all_button=ttk.Button(row,text='Export all cases',command=self.export_all);self.export_all_button.pack(side='right')
        row2=ttk.Frame(tab);row2.pack(fill='x',padx=8,pady=3)
        ttk.Label(row2,text='Historical cutoff (original mode only):').pack(side='left');self.cutoff=tk.StringVar()
        self.cutoff_entry=ttk.Entry(row2,textvariable=self.cutoff,width=28,state='disabled');self.cutoff_entry.pack(side='left',padx=6)
        ttk.Label(row2,text='ISO 8601 with timezone').pack(side='left')
        self.batch_summary=tk.StringVar(value='30 prefilled records / 10 cases | Document analysis ready')
        ttk.Label(tab,textvariable=self.batch_summary).pack(anchor='w',padx=8,pady=3)
        self.results=self.add_text(tab)
    def set_mode(self):
        original=self.analysis_mode.get().startswith('Historical')
        self.cutoff_entry.configure(state='normal' if original else 'disabled')
        self.batch_button.configure(state='disabled' if original else 'normal')
    def run_all(self):
        if self.analysis_mode.get().startswith('Historical'):
            messagebox.showinfo('Batch mode','Batch analysis uses prefilled retrospective documents.');return
        cases=list(self.cases);records={c['id']:evidence_for(self.store,c['id']) for c in cases}
        gateway=self.gateway() if self.use_gemini.get() else None
        def progress(n,total,r):self.jobs.put(('batch_progress',r['case_id'],(n,total,r),None))
        self.begin_job('batch',lambda:run_batch(cases,records,gateway,progress))
    def export_all(self):
        path=filedialog.asksaveasfilename(defaultextension='.zip',initialfile='FireWatch_All_10_Cases.zip',filetypes=[('ZIP archive','*.zip')])
        if path:
            try:
                from research import export_all_cases
                export_all_cases(self.store,path);self.status.set('All 10 case bundles exported.')
            except OSError as exc:messagebox.showerror('Export',str(exc))
    def make_pilot_tab(self):
        self.pilot_tab=ttk.Frame(self.tabs);self.tabs.add(self.pilot_tab,text='Reviewed pilot')
        row=ttk.Frame(self.pilot_tab);row.pack(fill='x',padx=8,pady=8)
        ttk.Label(row,text='Gironde | Original CEMS provider maps | AI technical review complete; human approval pending').pack(anchor='w')
        controls=ttk.Frame(self.pilot_tab);controls.pack(fill='x',padx=8,pady=5)
        points=pilot_dataset()['checkpoints']
        self.checkpoint=ttk.Combobox(controls,state='readonly',values=[p['id']+' | '+p['cutoff'] for p in points],width=42);self.checkpoint.pack(side='left');self.checkpoint.current(1)
        self.pilot_run_button=ttk.Button(controls,text='Run pilot cutoff',command=self.run_pilot);self.pilot_run_button.pack(side='left',padx=6)
        ttk.Button(controls,text='Open first reviewed dossier',command=self.open_first_dossier).pack(side='left',padx=6)
        files=ttk.Frame(self.pilot_tab);files.pack(fill='x',padx=8,pady=4)
        self.product_choice=ttk.Combobox(files,state='readonly',values=[p['id']+' | '+p['aoi']+' | '+p['kind'] for p in pilot_dataset()['products']],width=64);self.product_choice.pack(side='left');self.product_choice.current(0)
        ttk.Button(files,text='Open original PDF',command=self.open_original).pack(side='left',padx=6)
        self.pilot_text=self.add_text(self.pilot_tab)
        d=pilot_dataset();lines=['FIRST CURATED DOSSIER — '+d['case_id'],d['scope'],'','TECHNICAL REVIEW: '+technical_review()['decision'],'Reviewer: Codex (AI assistant). Human approval: PENDING.','']
        for p in d['products']:
            b=availability_bounds(p);lines += [p['id']+' — '+p['aoi']+' / '+p['kind'],'Source: '+p['source_url'],'Observed (UTC): '+p['observed_at'],'Map production day (UTC): '+p['production_on_utc'],'Portal delivery (NO TIMEZONE): '+p['delivery_local_without_timezone'],'Conditional interval: '+b['lower']+' to '+b['upper'],'SHA-256: '+p['sha256'],'Warnings: '+str(p['warnings']),'']
        lines += ['CHECKPOINT RATIONALES']+[p['id']+': '+p['rationale'] for p in d['checkpoints']]+['','INTEGRITY CHECKS',json.dumps(verify_artifacts(),indent=2),'','Use the original PDF and review controls before accepting a research record. No original availability or human approval is fabricated.']
        self.show(self.pilot_text,'\n'.join(lines))
    def open_original(self):
        import os
        product=pilot_dataset()['products'][self.product_choice.current()]
        if next(c['status'] for c in verify_artifacts() if c['product_id']==product['id'])!='MATCH':
            messagebox.showerror('Original file','The local original does not match its recorded SHA-256.');return
        path=artifact_path(product)
        if os.name=='nt':os.startfile(str(path))
        else:webbrowser.open(path.as_uri())
    def select_pilot_case(self):
        self.choice.current(7);self.load()
    def open_first_dossier(self):
        self.select_pilot_case();self.refresh_history()
        self.history.set('FW-RC-008-PILOT-BASELINE-v1');self.select_run();self.tabs.select(self.analysis_tab)
    def run_pilot(self):
        cutoff=pilot_dataset()['checkpoints'][self.checkpoint.current()]['cutoff']
        self.select_pilot_case();gateway=self.gateway() if self.use_gemini.get() else None
        self.begin_job('analysis',lambda:analyze_pilot(cutoff,gateway),case_id='FW-RC-008');self.tabs.select(self.analysis_tab)
    def gateway(self):
        return GeminiGateway(self.api_key.get(),self.model.get())
    def begin_job(self,kind,fn,case_id=None):
        if self.busy:
            messagebox.showinfo('Working','Wait for the current request to finish.');return
        self.busy=True;self.choice.configure(state='disabled');self.run_button.configure(state='disabled');self.probe_button.configure(state='disabled');self.pilot_run_button.configure(state='disabled');self.batch_button.configure(state='disabled');self.mode_choice.configure(state='disabled')
        self.status.set('Working… Gemini requests have bounded timeouts and retries.')
        def worker():
            try:self.jobs.put((kind,case_id,fn(),None))
            except Exception:self.jobs.put((kind,case_id,None,'The task failed. No credentials or raw exception details were logged.'))
        threading.Thread(target=worker,daemon=True).start()
    def poll_jobs(self):
        try:
            kind,case_id,result,err=self.jobs.get_nowait()
            if kind=='batch_progress':
                n,total,r=result
                try:self.store.save_run(r)
                except Exception:self.status.set('A batch run could not be saved; check database permissions.')
                self.batch_summary.set(f'{n}/{total} completed | {case_id} | {r["mode"]}')
            else:
                self.busy=False;self.choice.configure(state='readonly');self.run_button.configure(state='normal');self.probe_button.configure(state='normal');self.pilot_run_button.configure(state='normal');self.mode_choice.configure(state='readonly');self.set_mode()
                if err:messagebox.showerror('Task error',err);self.status.set(err)
                elif kind=='probe':
                    self.show(self.probe_text,result);self.status.set('Connection: '+result['source']+' / '+result['reason'])
                elif kind=='batch':
                    self.batch_summary.set(f'{len(result)}/10 document analyses completed; human review pending.')
                    summary=['BATCH DOCUMENT ANALYSIS — human review pending','']
                    for r in result:summary.append(r['case_id']+' | '+r['status']+' | '+r['mode'])
                    summary += ['','Completion counts executions, not prediction accuracy or historical validation.','Select a case and its saved run under History & review to read its report.']
                    self.show(self.results,'\n'.join(summary));self.refresh_history();self.status.set('Batch complete. Export all cases to save the ten dossiers and reports.')
                else:
                    try:
                        self.store.save_run(result);self.refresh_history();self.history.set(result['id']);self.select_run()
                        self.status.set('Saved run | '+result['mode']+' | '+result['status'])
                    except Exception:messagebox.showerror('Save error','The run could not be saved. Check database permissions.')
        except queue.Empty:pass
        self.root.after(100,self.poll_jobs)
    def refresh_history(self):
        self.history['values']=[x['id'] for x in self.store.runs(self.case['id'])]
    def run(self):
        from core import timestamp
        try:
            case_id=self.case['id'];gateway=self.gateway() if self.use_gemini.get() else None
            if self.analysis_mode.get().startswith('Retrospective'):
                evidence=evidence_for(self.store,case_id)
                self.begin_job('analysis',lambda:analyze_research(case_id,evidence,gateway),case_id)
            else:
                cutoff=self.cutoff.get();timestamp(cutoff);evidence=self.store.evidence(case_id)
                self.begin_job('analysis',lambda:analyze(case_id,cutoff,evidence,gateway),case_id)
        except (ValueError,OSError) as exc:messagebox.showerror('Analysis',str(exc))
    def make_gemini_tab(self):
        tab=ttk.Frame(self.tabs);self.tabs.add(tab,text='Gemini settings')
        ttk.Label(tab,text='Gemini Evidence + Gemini Critic | Only selected admitted evidence text is sent to Google.').pack(anchor='w',padx=8,pady=10)
        ttk.Label(tab,text='API key (session only; or configure GEMINI_API_KEY / local .env):').pack(anchor='w',padx=8)
        try:key=load_key()
        except OSError:key=''
        self.api_key=tk.StringVar(value=key)
        ttk.Entry(tab,textvariable=self.api_key,show='*').pack(fill='x',padx=8,pady=6)
        ttk.Label(tab,text='Model ID:').pack(anchor='w',padx=8)
        self.model=tk.StringVar(value=MODEL);ttk.Entry(tab,textvariable=self.model).pack(fill='x',padx=8,pady=6)
        self.use_gemini=tk.BooleanVar(value=False)
        ttk.Checkbutton(tab,text='Enable Gemini for analysis (sends admitted claims to Google)',variable=self.use_gemini).pack(anchor='w',padx=8,pady=6)
        self.probe_button=ttk.Button(tab,text='Test Gemini connection (one diagnostic request; retries on transient errors)',command=lambda:self.begin_job('probe',self.gateway().probe));self.probe_button.pack(anchor='w',padx=8,pady=6)
        self.probe_text=self.add_text(tab)
        self.show(self.probe_text,'Not tested. The key is masked and is not saved by the application. Offline analysis remains available. The prefilled document mode is ready for analysis. The original-record mode still requires contemporaneous evidence. A connection test sends no case evidence. Model access depends on your Google account. No automatic model substitution is performed.')
    def make_review_tab(self):
        tab=ttk.Frame(self.tabs);self.tabs.add(tab,text='History & review')
        row=ttk.Frame(tab);row.pack(fill='x',padx=8,pady=8)
        ttk.Label(row,text='Saved run:').pack(side='left');self.history=ttk.Combobox(row,state='readonly',width=42);self.history.pack(side='left',padx=6);self.history.bind('<<ComboboxSelected>>',lambda e:self.select_run())
        self.reviewer=tk.StringVar();self.review_note=tk.StringVar();self.review_decision=tk.StringVar(value='REQUEST_CORRECTION')
        for label,var in [('Reviewer',self.reviewer),('Rationale',self.review_note)]:
            ttk.Label(tab,text=label).pack(anchor='w',padx=8);ttk.Entry(tab,textvariable=var).pack(fill='x',padx=8,pady=3)
        ttk.Combobox(tab,state='readonly',textvariable=self.review_decision,values=['ACCEPT_RESEARCH_RECORD','REQUEST_CORRECTION']).pack(fill='x',padx=8,pady=6)
        ttk.Button(tab,text='Save research review',command=self.review).pack(anchor='w',padx=8)
        self.review_checks={}
        for key,label in [('source_files_checked','I checked the original provider files'),('temporal_assumptions_understood','I understand conditional temporal bounds and unresolved metadata'),('research_limits_understood','I accept research scope only; no operational or responder-knowledge claim')]:
            value=tk.BooleanVar();self.review_checks[key]=value;ttk.Checkbutton(tab,text=label,variable=value).pack(anchor='w',padx=8)
        self.review_text=self.add_text(tab)
    def select_run(self):
        for value in self.review_checks.values():value.set(False)
        self.current_run=next((r for r in self.store.runs(self.case['id']) if r['id']==self.history.get()),None)
        if self.current_run:
            self.show(self.results,render_report(self.current_run));self.show(self.trace,self.current_run['trace']);self.show(self.review_text,self.store.reviews(self.current_run['id']))
    def review(self):
        try:
            if not self.current_run:raise ValueError('Select a saved run first.')
            if self.current_run.get('analysis_mode')=='bounded_source_product_review':
                save_human_review(self.store,self.current_run['id'],self.reviewer.get(),self.review_decision.get(),self.review_note.get(),{k:v.get() for k,v in self.review_checks.items()})
            else:
                self.store.review(self.current_run['id'],self.reviewer.get(),self.review_decision.get(),self.review_note.get())
            self.select_run();self.status.set('Research review saved. No operational authorization is issued.')
        except ValueError as exc:messagebox.showerror('Human review',str(exc))
    def export(self):
        path=filedialog.asksaveasfilename(defaultextension='.zip',initialfile=self.case['id']+'_research_bundle.zip',filetypes=[('ZIP archive','*.zip')])
        if path:
            try:export_bundle(self.store,self.case['id'],path);self.status.set('Case bundle exported with evidence, runs, reviews, traces and checksums.')
            except OSError as exc:messagebox.showerror('Export',str(exc))

if __name__=='__main__':
    root=tk.Tk();App(root);root.mainloop()
