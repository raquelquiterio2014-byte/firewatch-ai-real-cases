# Revision 2 — Fresh web research and human-intervention reassessment

## What changed

The earlier implementation interpreted a prefilled document set and always required human research review. This did not implement fresh source discovery or a changing review recommendation. The Revision 2 **Web updates** workspace corrects that mismatch.

Each explicit click runs a new Gemini request with Google Search enabled, registers provider-cited passages, compares them with prior discoveries and runs dependent evidence and Critic assessments. It preserves sources, queries, retrieval times, findings, open issues, model-supported issue resolutions, call audits, previous-run links and immutable snapshots in SQLite.

## Windows / PyCharm

1. Keep your Revision 1 folder. Extract the new folder **FireWatch_AI_Real_Cases_Revision_2**.
2. Run `main.py` with Python 3.12, or double-click `run_gui.bat`. No additional packages are required.
   The named ZIP includes the three original map PDFs. If you clone or download the GitHub source archive instead, run `py -3.12 download_originals.py` first to restore the map files from the official provider and verify their recorded hashes. This is separate from live Gemini web discovery.
3. Open **Gemini settings**, enter your masked session key and choose an available model. Default remains `gemini-2.5-flash`; the app never silently changes models. A JSON connection probe does not validate search access.
4. Select one of the ten historical cases. Open **Web updates**, enter a focused research question and click **Search updates & reassess**. This explicitly enables external search and subsequent analysis, independently of the older analysis-mode checkbox.
5. Inspect `Newly discovered records`, the research-intervention recommendation and the reasons. Open **cited sources & search suggestions** to see the provider-linked passages. The returned links can be Google redirect URLs; no original-source identity or historical availability is inferred from them.
6. Repeat the search. A new run is saved even if the same passages are returned. Exact same passage/source combinations do not create duplicate records. Paraphrases, new source links or changed source contents may produce new records; the counter is not a count of newly published documents or independently new facts.
7. Restart and load a saved update under **History & review**. Verify its original sources, recommendation and previous-run link. Export the case ZIP to retain discoveries, research reports, source/suggestion HTML, traces, human reviews and checksums.

Console equivalents, from the extracted project folder:

```powershell
py -3.12 -m unittest discover -s tests -v
py -3.12 run_update.py --case FW-RC-008 --output exports\gironde-update.json --txt exports\gironde-update.txt
```

The console reads `GEMINI_API_KEY` or a local `.env`; the masked GUI key is session-only and is not automatically available to a separate terminal process. Without a key the command records explicit fallback and returns exit code 2. A complete validated three-stage analysis returns 0; this does not imply real-world accuracy or mandatory agreement with earlier runs.

## How the recommendation changes

- **REQUIRED:** either model identifies an issue, an earlier issue remains open, a necessary research gap remains, or search/citation/output validation fails.
- **NOT_REQUESTED:** a fresh cited search and both valid assessments complete without requesting intervention, no earlier issue remains open and local checks pass. The interface explicitly states that this is not human approval, an all-clear or operational authorization.

Old issues have stable IDs. Both assessments must explicitly support closing the same issue using at least one newly discovered record. Otherwise the issue stays open. Generic model review requests and research gaps are also retained as issues. Completed historical runs and later human acceptance/rejection remain separate and immutable. A failed search never silently becomes a successful new analysis.

The Critic is a separate request using the same configured model and the evidence assessment. It is not an independent human reviewer or necessarily an independent model. These checks validate structure and citation references, not the correctness of the model's interpretation.

## Time and scope

The ten cases are historical. New web research can discover publications or corrections available today about those old events. That is different from live wildfire monitoring. Current research is not filtered by the old Landiras event checkpoint; strict historical-cutoff mode is still available separately and keeps its original admission policy.

Search-grounded passages are model syntheses, not verbatim quotes from fetched original pages. Exact excerpts used by the subsequent assessments are checked against those registered syntheses. A search citation does not authenticate a source, confirm a fire or establish responder knowledge. Original publication and event-availability fields remain null when not independently established.

## Bounds and failures

One refresh has at most three logical requests: Search, Evidence, Critic. Each request has at most three attempts with a 25-second timeout and bounded backoff for transient failures. Invalid shapes/citations do not receive repeated guesses. Up to 30 cited passages are accepted per search, and the latest 40 registered passages are selected for analysis. Omitted/invalid grounding supports or a reached context limit trigger human review. Large prompts fail explicitly instead of silently truncating required evidence.

Closing the app during the worker can lose that current update; completed saved updates remain. Concurrent updates cannot overwrite a newer case history: the predecessor is checked under a database write transaction. No periodic scheduling or automatic source-page scraping is implemented. Open cited links explicitly to inspect the underlying material.

## Acceptance status

**101 development tests passed**, including 24 new offline tests for grounded discovery, citation/URL checks, retries/redaction, changing recommendations, retained issues, two-assessment resolutions, stale-history protection, restart, deduplication and exports. The three original Copernicus PDFs still match their recorded hashes. Live search with a real account and manual target-Windows visual checks remain pending. Source grounding is implemented according to the official [Google Search grounding guide](https://ai.google.dev/gemini-api/docs/generate-content/google-search).
