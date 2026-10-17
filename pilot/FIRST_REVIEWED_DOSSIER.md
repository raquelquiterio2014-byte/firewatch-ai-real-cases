# First curated and technically reviewed dossier

**FireWatch AI — Real Cases v0.4** · **FW-RC-008** · Gironde, France · July 2022

Review date: 17 October 2026. Reviewer: Codex (AI assistant). Review type: AI-assisted technical source review. Decision: accept for conditional document research with limitations. Independent human approval: **PENDING**.

## Research question and boundary

What can the original CEMS mapping products support at explicitly stated research checkpoints, when observation, production and delivery are treated as different times?

The dossier covers the Landiras and La Teste-de-Buch areas of interest within activation EMSR592. It does not reconstruct evacuation decisions, actual responder receipt or field operations. The three downloaded provider PDFs are processed mapping products, not raw satellite observations independently reprocessed by this project.

## Sources and local originals

Copernicus Emergency Management Service (© 2022 European Union), EMSR592:

- Landiras, AOI01: First Estimate Map, version 1 — product P01.
- La Teste-de-Buch, AOI02: First Estimate Map, version 1 — product P02.
- Landiras, AOI01: Delineation Map, version 1 — product P03.

The unchanged originals, their source links, producer credits and SHA-256 hashes are in `originals/` and `data/curated_pilot.json`. Full attribution and provider notices are retained. The source portal is https://mapping.emergency.copernicus.eu/activations/EMSR592/DELINEATION/.

All three PDFs were downloaded, text-extracted and rendered for visual source inspection. Their download hashes establish local file identity, not independent verification of the underlying measurements or historical public accessibility.

## Temporal reasoning

The maps print observation and production records under a UTC heading. The portal displays delivery timestamps without a timezone. Production dates have day precision; acquisition time must never become availability time.

The pilot uses a conservative research interval. A timezone-unspecified portal stamp is evaluated across civil offsets from UTC−12 to UTC+14. Its earliest and latest possible UTC instants are combined conservatively with the observation and UTC production-day interval. The exact rule is versioned as BOUNDED_DELIVERY_V1 in the dataset and implemented in `pilot.py`.

This method assumes that the portal delivery card relates to the downloaded version. No historical web capture or version-delivery linkage independently confirms that assumption. Therefore all admissions are conditional and **strict responder-time replay remains ineligible**.

A specific issue is retained for P02: the portal records delivery on 16 July while the PDF records production on 17 July. The unknown portal timezone means this is a calendar-date difference requiring reconciliation, not proof of a definite chronology contradiction.

## Three justified checkpoints

| Checkpoint | UTC cutoff | Expected conservative admission | Reason |
|---|---|---|---|
| EARLY | 17 July 2022, 00:00 | None | The first product's possible availability interval still crosses the cutoff. |
| PRIMARY | 17 July 2022, 12:00 | P01 only: 2 evidence records | Admits the first Landiras estimate after its upper bound; withholds P02 and the later delineation. |
| LATER | 18 July 2022, 06:00 | P01, P02 and P03: 6 records | Allows source comparison after all conservative upper bounds. |

These are research test checkpoints. They are not observed emergency decision times and do not prove what a particular operator received.

## Findings and limits

The primary checkpoint supports inspecting the Landiras first-estimate burned-area depiction and its coarse product limitations. Four records from the other products are withheld. In particular, later mapped exposure estimates never enter the primary model prompt.

The later checkpoint supports inspecting all three source products. Mapped population exposure is an estimate, not a casualty count or confirmed occupancy. A road appearing on a basemap does not establish passability. Product differences may reflect changed observations, resolution and mapping methods; they do not automatically measure fire growth.

The AI-assisted technical review checks source identity, file integrity, dates, uncertainty handling, scoped interpretation and temporal exclusion. Its result and limitations are included in `data/pilot_technical_review.json`. That review is bound to the dataset hash. It is not an expert fire-service review or a human approval.

## Human completion

Open **Reviewed pilot**, inspect the source PDFs and the first dossier report, then use **History & review** to select the run, enter the researcher's name and rationale, and check the three source/temporal/scope confirmations. Accept or request correction. Reviews are stored separately, linked to the exact run hash, and never rewrite original evidence or grant operational authority.

Until that action is performed by a person, the dossier remains technically reviewed by AI and awaiting independent human approval.
