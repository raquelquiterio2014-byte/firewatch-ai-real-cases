# FireWatch AI — Real Cases v0.5

Web discovery and research reassessment · Raquel Cruz · 30 October 2026

## Corrected workflow: find new information and reassess human intervention

The new **Web updates** workspace implements the intended discovery cycle: **fresh Gemini + Google Search → source-linked passages → evidence assessment → separate Critic assessment → reassessed need for human research intervention → new saved run**. Each click on **Search updates & reassess** makes a new external search. This is not a scheduled background monitor.

Unlike the earlier document-only workflow, the input set can grow. Provider search queries, citation links, retrieved times, attributed passages and call outcomes are saved. Exact passage/source combinations are deduplicated. A newly discovered record may describe an old event or an old publication; retrieval time is never presented as publication time or historical availability. These records are **search-grounded model syntheses**, not original-source quotations or independently authenticated facts.

The new research recommendation is **REQUIRED** or **NOT_REQUESTED**. Either assessment can request intervention; local checks require it after search/citation/output failures, unresolved gaps or open issues. An earlier issue stays open unless new cited evidence supports a resolution and both the evidence assessment and the Critic explicitly agree. Such a resolution is labeled model reassessment, not human approval. Earlier runs and human acceptance records are never overwritten. This recommendation concerns document research, not firefighting decisions, and does not establish operational safety.

The source-search request enables `google_search` and accepts only returned segments linked to provider grounding sources and actual search-query metadata. The subsequent two structured requests cannot browse and receive only the selected evidence. There are at most **3 logical calls / 9 HTTP attempts per refresh** (25-second attempt timeout, bounded transient-error retries). Missing key and invalid outputs produce explicit fallback and retain the previous evidence. Source suggestions and citations can be opened from the interface and are included in case exports.

**Development verification:** 101 automated tests passed, including 24 new offline search/reassessment tests. Original PDF hashes and all 77 earlier checks still pass. Actual live Google Search/Gemini and manual Windows acceptance of v0.5 remain pending. Transport fixtures are explicitly labeled `injected_transport`.

Start with [the v0.5 guide](docs/WEB_UPDATES_V05.md). The v0.4 workflows below remain available for document research and historical-cutoff study. Their fixed historical cutoffs do not apply to the new current-research workspace.

Ten real wildfire case dossiers now include **30 prefilled source-attributed research records**, three per case. Select a case and click **Run analysis**, or click **Analyze all 10 cases**. No manual evidence registration or event-time cutoff is needed for the default document mode.

## Previous v0.1–v0.4 development history

| Release | Main change | Development validation |
|---|---|---|
| v0.1 | Ten sourced case registrations, fifteen source leads, English desktop UI, original-record admission checks, SQLite and exports | 16 automated tests |
| v0.2 | Optional Gemini Evidence and Gemini Critic, structured output/citation checks, connection probe and explicit fallback | 37 automated tests; provider responses simulated |
| v0.3 | Thirty prefilled source-attributed document records, individual/batch document analysis and readable reports | 54 automated tests; all ten document cases executed offline |
| v0.4 | Three original Gironde CEMS maps, six curated records, conditional temporal bounds, three checkpoints, AI technical review and linked human research checklist | 77 automated tests; primary pilot execution and export verified offline |

These counts describe the development checks for each milestone. They are not historical prediction scores. Authenticated live Gemini validation, independent human approval of the first pilot and target Windows GUI visual acceptance remain pending for this project.

This repository contains v0.5 source, extending the earlier research cycle. Earlier version numbers describe the development sequence; this initial publication does not claim separate Git tags, releases or a commit history for v0.1–v0.3.

## First curated and technically reviewed dossier

The new **Reviewed pilot** workspace opens on **Gironde — Landiras / La Teste-de-Buch**, with three unchanged original Copernicus EMSR592 provider PDFs, six source-attributed records, file hashes, three justified research checkpoints and a prepared first report. The existing ten-case, thirty-record document workflow remains available.

**Review identity:** Codex (AI assistant) performed the technical source review. Independent human approval remains pending. No signature or approval has been created on behalf of Raquel or any other person.

Use **Open original PDF**, **Open first reviewed dossier** and **Run pilot cutoff**. The source/temporal research checklist in **History & review** records a person's name, rationale and decision against the exact run hash. Acceptance does not change immutable evidence or establish operational authority.

The original map PDFs provide observation and production records. Their public portal delivery stamps omit timezones, and one product has delivery/production calendar dates that differ. The method therefore uses explicitly conditional conservative intervals. At the primary checkpoint only the first Landiras estimate is admitted; later records are withheld. **Strict responder-time replay remains ineligible** because original availability and downloaded-version-to-delivery linkage are not independently verified.

Read `pilot/FIRST_REVIEWED_DOSSIER.md`, `docs/CUTOFF_METHOD.md`, `data/curated_pilot.json` and `data/pilot_technical_review.json`. The first prepared run and readable report are in `pilot/`. Other cases remain ready for document analysis; deep original-product curation has been completed only for this first pilot.

## Start on Windows / PyCharm

1. Extract the ZIP completely.
2. Open the extracted folder in PyCharm with Python 3.12.
3. Run `main.py`, or double-click `run_gui.bat`.
4. The app opens on **Web updates**; configure the key to search and reassess. **Reviewed pilot** retains the original-product dossier.
5. To run all ten document cases, open **Analysis**. The **Open view** menu exposes every tab on smaller screens.
6. Keep **Retrospective documents (prefilled)** selected, then run one case or all ten.

No pip installation is needed. Standard Python with Tkinter is sufficient.

## User manuals

- [English user manual](docs/FireWatch_AI_v0_4_User_Manual_EN.pdf)
- [Manual em português](docs/Manual_FireWatch_AI_v0_4_PT.pdf)

Step-by-step setup, pilot and ten-case execution, report reading, Gemini settings, review and export.

## Gemini

Open **Gemini settings**, enter a masked session key, test the connection and enable Gemini for analysis. Keys can also be supplied through `GEMINI_API_KEY` or a local `.env` copied from `.env.example`. The default model is editable: `gemini-2.5-flash`. Model access depends on your Google account. The app never substitutes a model automatically.

Gemini Evidence reviews the admitted claim text; Gemini Critic receives that structured output and the same evidence. Local checks enforce JSON shape, known evidence IDs, matching quoted claim excerpts and mandatory human review. They do not establish semantic correctness. The deterministic report always remains available. These older document and cutoff modes do not browse. The separate v0.5 Web updates mode explicitly enables Google Search.

A full batch normally uses two Gemini calls per case, up to 20 logical calls, with bounded retries for transient errors. After persistent quota/authentication/model-access failure in one case, remaining cases complete using an explicitly marked fallback without further API calls. The interface remains responsive. Closing the app before a result is received can lose the current case execution; already saved batch cases remain stored.

## Three distinct analysis workflows

| Mode | Inputs | Time handling | Output |
|---|---|---|---|
| Retrospective documents — default | 30 prefilled research records | Event periods and day-level publication dates; unknown exact availability remains null | Source-attributed findings, topics, research gaps, optional Gemini interpretation |
| Curated original products pilot | Three original CEMS maps / six records | Conditional conservative intervals; justified checkpoints | First technically reviewed source dossier; human acceptance pending |
| Historical cutoff | Manually registered original records from the previous version | Explicit original availability and timezone-aware cutoff required | Admission/readiness assessment using only eligible original records |

Neither the prefilled document records nor the conditional pilot records **can enter strict historical-cutoff mode**. A report published after a fire is valid input for document research, not evidence of what responders knew during that fire. Document review uses a research review date, not an event-time cutoff. No precise timestamp has been invented to bypass admission rules.

## Included dossiers

| Case | Country | Period | Prefilled records |
|---|---|---|---|
| Camp Fire | USA | 2018 | 3 |
| Lahaina | USA | 2023 | 3 |
| Pedrógão Grande | Portugal | 2017 | 3 |
| Pantanal | Brazil | 2020 | 3 |
| Black Summer, southeastern Australia | Australia | 2019–2020 | 3 |
| Fort McMurray | Canada | 2016 | 3 |
| Mati / eastern Attica | Greece | 2018 | 3 |
| Gironde, Landiras / La Teste-de-Buch | France | 2022 | 3 |
| Northern Evia | Greece | 2021 | 3 |
| Valparaíso / Viña del Mar | Chile | 2024 | 3 |

Each record includes an attributed paraphrase, publisher, source URL, passage locator, short search anchor, event period, publication date when established, date of content check and verification scope. Ten institutional webpages were inspected for the prefilled set; all 30 short anchors matched their retrieved text. The broader catalogue retains 15 source leads.

This is a preliminary curated document set, not a comprehensive raw incident dataset. Full reports and underlying records have not been independently authenticated. Multiple claims from one publication are not independent corroboration. Publication dates are day-level, and one source has no established publication date. Regional cases remain broader than individual local incidents. Missing access, exposure or weather context is reported rather than fabricated.

## Reports, traces and review

The dependent stages are Planner → Evidence → optional Gemini Evidence → Risk / Impact → Decision → deterministic Critic → optional Gemini Critic → Safety → Human Gate → Reporter.

The readable report lists documented findings with evidence IDs and source locators, covered/missing topics, distinct source counts, next research steps and optional model interpretations. The Risk / Impact stage organizes documented context; **severity is NOT_ESTIMATED**. All analyses require human research review. They do not issue operational commands, fire forecasts, evacuation routes or validated historical risk scores.

`RETROSPECTIVE_DOCUMENT_ANALYSIS_COMPLETED` means the document workflow ran. It is not proof of historical accuracy or a successful prediction. Batch completion counts executions, not a 10/10 evaluation score.

After a batch, select a case and its saved run in **History & review**. Save a named review linked to that run. **Export case ZIP** includes the source catalogue, original evidence if any, research evidence, immutable run snapshots, readable reports, reviews, traces and checksums. **Export all cases** produces ten nested case ZIPs plus a summary.

## Original maps and attribution

Copernicus Emergency Management Service (© 2022 European Union), EMSR592: Landiras (AOI01) First Estimate and Delineation Maps; La Teste-de-Buch (AOI02) First Estimate Map. Provider credits and third-party notices are retained inside the unchanged PDFs. See `originals/ATTRIBUTION.txt` and the provider citation guidance at https://mapping.emergency.copernicus.eu/about/citation-guidelines/. No raw satellite imagery is separately redistributed. Source hashes establish downloaded-file identity, not independent measurement accuracy or historical availability.

## Existing data

With both apps closed, copy your previous `workspace` folder into this version's folder before opening it. Existing original evidence, runs and reviews are retained; a separate `research_evidence` table is added. The 30 stable research IDs are imported idempotently, without overwriting rows or creating duplicates. Seed data is versioned in `data/research_evidence.json`.

Do not include private workspace databases or `.env` files in public repositories.

## Console option

```powershell
py -3.12 run_pilot.py
py -3.12 run_pilot.py --checkpoint LATER
py -3.12 run_pilot.py --strict
py -3.12 run_all.py
py -3.12 run_all.py --gemini
py -3.12 -m unittest discover -s tests -v
```

`run_all.py` defaults to offline analysis. `--gemini` explicitly enables external calls using the local key. Export output defaults to `FireWatch_All_10_Cases.zip` in the working directory.

## Validation and remaining work

The automated checks cover the document workflow, strict original mode and conditional source-product pilot, migration/idempotent seeding, all-ten execution, cutoff isolation, source metadata, citation validation, dependent Gemini calls, quota fallback, persistence and exports. Gemini transport tests use simulated responses; an authenticated live request and visual GUI check remain for the target Windows installation. Historical decision evaluation, independent corroboration, LangGraph, typed full-document provenance and operational modeling remain future work.

See `LEIA-ME-PRIMEIRO.txt`, `docs/GEMINI_SETUP_PT.md` and `docs/RESEARCH_PROTOCOL.md`. Three official CEMS map products are redistributed unchanged with attribution and their existing notices. The institutional article text and raw satellite scenes are not redistributed. Source anchors are short navigation aids. No open-source license is assigned automatically.

## Earlier v0.4 release scope

This closes the v0.1–v0.4 software iteration: sourced catalogue, prefilled document analysis, optional Gemini integration, original source-product curation, justified conditional checkpoints, a first AI-technically-reviewed dossier, human review and export. It does not claim completion of independent historical validation or original-product curation for all ten cases.
