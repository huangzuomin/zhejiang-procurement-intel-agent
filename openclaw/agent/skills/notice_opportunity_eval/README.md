# notice_opportunity_eval

Evaluate a procurement notice or generated opportunity card for media/digital business fit.

Use when the user asks whether a project is worth following, why it is A/B/C/D, what risks exist, or what action to take next.

## Local Core Modules

- `procurement_intel.classifier.classify_notice`
- `procurement_intel.scorer.score_notice`
- `procurement_intel.daily_pipeline.run_daily_pipeline`

## Opportunity Classes

- `A`: clear media/digital opportunity with enough response information.
- `B`: worth attention, often early signal or media-relevant with missing/uncertain fields.
- `C`: edge opportunity, usually generic information technology or adjacent service.
- `D`: excluded or no media business evidence.

## Column-Specific Actions

- `bid` / 招标公告: prefer immediate response review, procurement-file download, qualification checks, budget confirmation, and deadline tracking.
- `intention` / 采购意向公开: prefer early follow-up, requirement discovery, case preparation, and pre-positioning.

## Required Evidence

Use only fields present in the cleaned notice or opportunity card:

- title
- buyer
- budget
- deadline
- raw detail text
- classification evidence
- source column
- risks and missing fields

## Output Shape

For a single project, answer with:

- conclusion and opportunity class
- source column and notice type
- evidence
- risks
- missing or undisclosed fields
- recommended action
- detail URL

## Boundary

- Do not promote generic IT projects as media opportunities without explicit website, content, communication, advertising, display, GEO, video, or operation evidence.
- Do not invent budget, deadline, buyer, procurement file content, eligibility requirements, or historical facts.
- Refuse tender registration, bid submission, payment, contract signing, or other execution actions.
