# 浙江政府采购情报 Agent 项目说明

## 项目定位

本项目是一个 OpenClaw 原生 Agent 开发仓库，目标是监测浙江政府采购网公开公告，识别与媒体、数字化、宣传、展陈、平台建设等业务相关的采购机会，并生成可读的今日采购机会简报。

当前项目不执行投标、不登录网站、不提交表单，也不绕过验证码。它只处理公开公告数据，并以低频采集、可审计流水线和本地问答为边界。

## 核心能力

- 双栏目采集：`采购意向公开` 和 `招标公告`。
- 详情页补全：补充采购人、预算、截止时间、公告正文等字段。
- 数据清洗：统一公告结构，保留来源栏目与分类编码。
- 机会评分：输出 A/B/C/D 机会等级和推荐动作。
- 日报生成：按栏目、媒体相关机会、字段风险分区生成 Markdown 简报。
- 本地 QA：基于 `opportunity_cards.json` 回答标题、采购人、栏目、等级等检索问题。
- 部署干跑：生成 OpenClaw runtime 包装清单，不执行真实部署。

## 架构

```text
浙江政府采购网公开栏目
  -> scripts/zfcg_browser_scraper.js
  -> scripts/run_daily_pipeline.py
  -> src/procurement_intel/
  -> cleaned_notices.json
  -> opportunity_cards.json
  -> quality_report.json
  -> daily_brief.md
  -> scripts/query_opportunity_cards.py
```

OpenClaw Agent 技能文档位于：

```text
openclaw/agent/skills/
```

工具层代码位于：

```text
src/procurement_intel/
scripts/
```

## 快速验证

```bash
python3 -m pip install pytest
npm install
bash scripts/validate.sh
```

使用随仓库发布的公开样例 fixture 生成日报：

```bash
python3 scripts/run_daily_pipeline.py tests/fixtures/zfcg_browser_two_columns_60.json --today 2026-06-09 --output-dir reports/demo-daily-pipeline
```

基于机会卡片问答：

```bash
python3 scripts/query_opportunity_cards.py reports/demo-daily-pipeline/opportunity_cards.json "今天有哪些 A/B 机会？"
```

## 真实采集

默认目标栏目：

- `采购意向公开`
- `招标公告`

低频采集命令：

```bash
node scripts/zfcg_browser_scraper.js --targets intention,bid --limit 30 --detail-limit 30 --output reports/$(date +%F)/zfcg-browser-two-columns-30.json
```

生成日报：

```bash
python3 scripts/run_daily_pipeline.py reports/$(date +%F)/zfcg-browser-two-columns-30.json --today $(date +%F) --output-dir reports/$(date +%F)/daily-pipeline
```

## OpenClaw 部署准备

当前推荐包装方式是 Scheme A：将 `openclaw/agent/`、`src/procurement_intel/` 和批准的 `scripts/` 一起放入 Agent runtime workspace。

默认 runtime target 仅记录为：

```text
~/.openclaw/workspace-zhejiang-procurement-intel-agent
```

本仓库不会自动部署到 runtime。部署前先运行：

```bash
python3 scripts/prepare_deploy_dry_run.py --json
```

真实部署必须由用户明确授权后再执行。

## 开源边界

仓库包含源码、Agent 技能文档、测试和公开样例 fixture。以下内容不应进入开源仓库或 runtime 包：

- `.env`、密钥、令牌、Cookie、浏览器登录态。
- `node_modules/`、`.venv/`、缓存目录。
- 运行生成的 `reports/`。
- 私有数据库或非公开采购材料。

## 当前状态

截至 2026-06-09，本地验证结果为：

```text
44 passed
```
