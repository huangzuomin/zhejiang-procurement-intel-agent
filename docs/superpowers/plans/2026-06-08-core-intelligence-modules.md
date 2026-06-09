# Core Intelligence Modules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first local, testable procurement intelligence core for classification, scoring, DingTalk brief rendering and bounded Q&A.

**Architecture:** Keep the implementation as pure Python modules under `src/procurement_intel/` so OpenClaw agent instructions can call a stable tool layer later. Tests use explicit fixture notices and opportunity cards, with no live network, no DingTalk secrets and no runtime deployment.

**Tech Stack:** Python standard library, pytest, Bash validation script.

---

### Task 1: Test Fixtures And Classification

**Files:**
- Create: `tests/test_classifier.py`
- Create: `src/procurement_intel/__init__.py`
- Create: `src/procurement_intel/models.py`
- Create: `src/procurement_intel/classifier.py`

- [ ] **Step 1: Write failing classifier tests**

Create tests covering website construction, new media operation, video production, generic IT edge cases, GEO evidence and unrelated notices.

- [ ] **Step 2: Run classifier tests and verify failure**

Run: `python -m pytest tests/test_classifier.py -v`
Expected: import failure or missing implementation failure.

- [ ] **Step 3: Implement minimal classifier**

Implement `Notice`, `ClassificationResult`, category keywords, evidence extraction and conservative generic IT handling.

- [ ] **Step 4: Run classifier tests and verify pass**

Run: `python -m pytest tests/test_classifier.py -v`
Expected: all classifier tests pass.

### Task 2: Scoring

**Files:**
- Create: `tests/test_scorer.py`
- Create: `src/procurement_intel/scorer.py`

- [ ] **Step 1: Write failing scorer tests**

Cover A/B/C/D classes, low budget risk, urgent deadline risk and missing information.

- [ ] **Step 2: Run scorer tests and verify failure**

Run: `python -m pytest tests/test_scorer.py -v`
Expected: import failure or missing implementation failure.

- [ ] **Step 3: Implement minimal scorer**

Implement opportunity class calculation, risk tags, recommended action and missing field notes.

- [ ] **Step 4: Run scorer tests and verify pass**

Run: `python -m pytest tests/test_scorer.py -v`
Expected: all scorer tests pass.

### Task 3: DingTalk Brief Rendering

**Files:**
- Create: `tests/test_briefing.py`
- Create: `src/procurement_intel/briefing.py`

- [ ] **Step 1: Write failing briefing tests**

Cover mixed A/B/C/D daily brief, empty-day brief and long brief truncation preserving A-class projects.

- [ ] **Step 2: Run briefing tests and verify failure**

Run: `python -m pytest tests/test_briefing.py -v`
Expected: import failure or missing implementation failure.

- [ ] **Step 3: Implement minimal renderer**

Implement DingTalk-ready text output with counts, class sections, compact risks and follow-up prompt.

- [ ] **Step 4: Run briefing tests and verify pass**

Run: `python -m pytest tests/test_briefing.py -v`
Expected: all briefing tests pass.

### Task 4: Bounded Q&A

**Files:**
- Create: `tests/test_qa.py`
- Create: `src/procurement_intel/qa.py`

- [ ] **Step 1: Write failing Q&A tests**

Cover exact project reference answers, fuzzy ambiguity and out-of-scope bid execution refusal.

- [ ] **Step 2: Run Q&A tests and verify failure**

Run: `python -m pytest tests/test_qa.py -v`
Expected: import failure or missing implementation failure.

- [ ] **Step 3: Implement minimal Q&A**

Implement deterministic matching and bounded answer rendering from existing opportunity cards only.

- [ ] **Step 4: Run Q&A tests and verify pass**

Run: `python -m pytest tests/test_qa.py -v`
Expected: all Q&A tests pass.

### Task 5: Validation And Agent Docs

**Files:**
- Modify: `scripts/validate.sh`
- Modify: `openclaw/agent/skills/daily_procurement_brief/README.md`
- Modify: `openclaw/agent/skills/notice_opportunity_eval/README.md`
- Modify: `openclaw/agent/skills/procurement_qa/README.md`
- Modify: `openclaw/agent/skills/keyword_strategy_tuning/README.md`
- Delete: `openclaw/agent/skills/example_skill/SKILL.md`
- Modify: `docs/decision_log.md`

- [ ] **Step 1: Extend validation**

Make `bash scripts/validate.sh` run `python -m pytest tests -v` when pytest tests exist, and fail on placeholder example skills.

- [ ] **Step 2: Update agent skill docs**

Document how each OpenClaw skill should use the local core modules and what it must refuse.

- [ ] **Step 3: Record implementation decision**

Append a decision log entry explaining the pure Python core slice.

- [ ] **Step 4: Run full validation**

Run: `bash scripts/validate.sh`
Expected: validation passes and pytest suite passes.

## Self-Review

- Spec coverage: Implements first-round classification, scoring, brief rendering and bounded Q&A. Live collection, storage and DingTalk sending remain out of this slice by design.
- Placeholder scan: No implementation placeholders in this plan.
- Type consistency: Tests and implementation will share `Notice`, `ClassificationResult` and `OpportunityCard` dataclasses.
