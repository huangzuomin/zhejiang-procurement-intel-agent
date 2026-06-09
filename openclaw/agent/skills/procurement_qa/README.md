# procurement_qa

Answer bounded questions about collected Zhejiang procurement notices and generated opportunity cards.

Use when users ask follow-up questions about the latest daily brief, known projects, A/B/C/D reasons, buyers, source columns, or immediate-response opportunities.

## Data Source

Read the latest generated opportunity cards JSON, normally:

```text
reports/<date>/daily-pipeline-sample/opportunity_cards.json
```

The runtime wrapper may expose this as a latest artifact path. If no cards file is available, say that no collected opportunity-card data is loaded.

## Local Core Module

Use:

```python
from procurement_intel.qa import answer_question_from_cards_file, load_opportunity_cards
```

Supported deterministic queries include:

- 今天有哪些 A/B 机会？
- 某项目为什么是 A/B/C/D？
- 招标公告中哪些需要立即响应？
- 按项目标题、采购人、栏目、机会等级检索。

## Answer Rules

- Base every answer on `opportunity_cards.json`.
- Include conclusion, column, buyer, budget/deadline if disclosed, evidence, risk, recommendation, uncertainty, and URL for single-project answers.
- For list answers, include opportunity class, title, column, buyer, and action.
- Ask for clarification when multiple projects match.
- Say no when the project cannot be found in collected data.

## Safety Boundary

- Do not fabricate undisclosed budget, deadline, buyer, procurement-file requirements, or eligibility facts.
- Refuse tender registration, bid submission, payment, contract signing, and other execution requests.
- Do not claim access to non-public procurement data.
