# Research protocol v0.4

## Default document mode

The prefilled set consists of thirty source-attributed paraphrases from ten institutional webpages, inspected on 17 October 2026. Each case has three research records. Source anchors are short literal navigation aids. The set is intended to run a document research workflow immediately, without demanding impossible exact timestamps from retrospective reports.

Event periods and source publication dates are distinct. Some publication dates are unknown. Exact observation and original availability timestamps remain null; no midnight or arbitrary hour is substituted. Source content checks do not establish original responder access. Full reports and raw data have not been independently authenticated, and three claims from one document count as one source.

The default workflow permits later reconstructions but labels every run as retrospective document analysis. It reports sourced claims and gaps, never a replay of information available during the fire. Review_as_of is the research review date. A dataset curated on 17 October 2026 is not represented as an archive already held on an earlier research date.

## Historical-cutoff mode

Original record registration remains separate and unchanged. This mode requires a contemporaneous record, exact availability verification and timezone-aware cutoff. Prefilled retrospective records are rejected in this mode. An acquisition time is not automatically a product release time; a later report cannot establish what a responder knew without reference to original records and an information-access assumption.

## Gemini and deterministic controls

Gemini receives admitted claim text, topics, IDs and temporal metadata appropriate to the selected mode. It receives no research catalogue, external tools or automatically retrieved full documents. The Critic also receives accepted Evidence output. Local validation checks JSON shape, IDs and literal excerpt correspondence to registered claims, not the semantic validity of an inference. All interpretations remain subject to human review. Prompts constrain the model to supplied evidence but cannot prove absence of latent historical knowledge.

Deterministic checks remain authoritative for evidence admission and research-use limits. Severity remains NOT_ESTIMATED. Missing context is reported rather than created. Known manually flagged conflicts hold the record for review; automated semantic conflict detection is not implemented.

## Evaluation meaning

Completing ten document runs is an execution result, not 10/10 historical accuracy. Evaluate a historical decision only after defining a task, matched spatial/temporal unit, original input set, human baseline and separate outcomes. Pantanal, Black Summer and other regional episodes need narrower local research boundaries before decision-level comparison.

## Persistence and corrections

Research records use stable versioned IDs in a separate SQLite table. Import is idempotent and does not overwrite existing rows or original records. A future dataset correction should receive a new version and explicit supersession handling rather than silently changing an existing run. Saved runs contain immutable evidence snapshots, traces, model status and linked human reviews. Existing runs are not rewritten by later reviews or registrations.

## Original-product pilot

The first deeper dossier uses three original CEMS provider-map PDFs. It has separate identity, file hashes, product observation times, production days, timezone-unspecified portal delivery stamps and conservative methodological availability bounds. Its AI technical review is bound to the dataset hash. Its first prepared run is imported idempotently into the local history.

Conditional product review is a third workflow, not a relaxation of strict original-record admission. The mapping from today's portal card to the downloaded historical version is unverified; no specific responder receipt is established. A human research acceptance records understood assumptions and source checks, never silently upgrades provenance. Review decisions remain linked to immutable runs and stored apart from the AI technical review.
