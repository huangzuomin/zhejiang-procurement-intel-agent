# Contributing

Thanks for your interest in improving this project.

## Development Setup

```bash
python3 -m pip install pytest
npm install
bash scripts/validate.sh
```

The Python modules live under `src/procurement_intel/`. Browser collection is implemented in `scripts/zfcg_browser_scraper.js`.

## Contribution Scope

Good first areas include:

- Parser fixes for public Zhejiang procurement notice pages.
- Safer opportunity scoring rules.
- Daily brief readability improvements.
- Fixture-based tests for edge cases.
- OpenClaw Agent skill documentation improvements.

Please keep changes small and testable. Live collection behavior should remain low-frequency and respectful of the public website.

## Safety Rules

- Do not commit secrets, cookies, tokens, private datasets, or runtime credentials.
- Do not add CAPTCHA bypass, login scraping, or form submission behavior.
- Do not turn the Agent into a bid-submission or procurement-execution tool.
- Use public procurement data only.

## Validation

Run this before submitting changes:

```bash
bash scripts/validate.sh
```

For deployment packaging checks, run:

```bash
python3 scripts/prepare_deploy_dry_run.py --json
```
