# 后续功能开发需求

## 文档目的

本文记录 2026-06-10 讨论形成的后续升级方向，供后续 Codex、OpenClaw Agent、运行服务器维护者在规划和实现时参考。

当前系统已经具备双栏目采集、详情补全、分类评分、日报生成、机会卡片、QA 和钉钉推送闭环。下一阶段的核心目标不是继续堆采集栏目，而是把系统从“采购公告雷达”升级为“采购机会生命周期情报库”。

## 当前基线

已跑通能力：

- 采购意向公开采集。
- 招标公告采集。
- 详情页补全。
- AM 全量简报。
- PM 增量简报。
- A/B/C/D 机会评分。
- 基于 `opportunity_cards.json` 的有限 QA。
- 钉钉群推送。
- GitHub 作为开发环境和运行服务器之间的代码同步源。

运行约束：

- 开发环境和运行服务器不在同一台机器。
- 运行服务器为 `100.91.229.7`。
- 运行服务器侧修复可能回传 GitHub。
- Codex 开发前必须先执行 `git pull --ff-only origin main`。
- 不直接修改 `~/.openclaw/`。
- 不绕过验证码，不登录采集，不提交表单。

## 需求总判断

### 可以立即落地

- 成交结果采集。
- 成交结果字段质量评估。
- SQLite 本地长期存储。
- AM/PM 增量状态入库。
- 项目生命周期初步关联。
- 采购人画像。
- 供应商画像。
- 价格基准初版。
- 系统健康报告。
- 历史 QA 初版。

### 需要数据沉淀后落地

- 赛道月报。
- 产品包反推。
- 采购单位年度采购规律。
- 供应商扩张方向。
- 采购意向转招标预测。
- 机会评分复盘优化。

### 暂不建议第一轮做

- 完整业务待办流转系统。
- 赢面预测。
- 强关系图谱判断。
- 审计化异常判断。
- 大屏 BI 或复杂后台。
- 把采集核心迁移到 n8n。

## 架构决策

### 数据采集是否迁移到 n8n

结论：不建议迁移采集核心到 n8n。

n8n 适合调度、告警、人工确认、多渠道分发和外部系统编排，但当前采集依赖浏览器翻页、详情补全、字段清洗、质量评估和回归测试。采集核心继续保留在 OpenClaw Agent 工具层和代码仓库中更稳。

如果后续引入 n8n，推荐边界是：

- n8n 触发 AM/PM/周报/月报流程。
- n8n 接收健康报告和失败事件。
- n8n 做人工确认或多渠道通知。
- 采集、解析、评分、入库、简报生成仍由本项目脚本和模块负责。

### 是否引入数据库

结论：应该引入数据库。

如果系统只生成当天日报，JSON 文件足够。但成交结果、生命周期、采购人画像、供应商画像、增量对比、历史 QA 和复盘都需要长期事实库。

第一阶段推荐：

```text
SQLite + JSON/Markdown 运行产物
```

SQLite 负责长期结构化数据，JSON/Markdown 继续作为每日运行产物、交付物和可回放快照。

### SQLite 还是 Supabase

结论：先 SQLite，预留 Supabase/Postgres 迁移口。

SQLite 适合当前阶段：

- OpenClaw runtime 本地运行。
- 单 Agent 写入。
- 无需额外服务和密钥。
- 易备份，易测试，易排查。
- 可直接支持增量、画像、生命周期和历史 QA。

Supabase/Postgres 适合后续阶段：

- 多人远程访问。
- Web 看板。
- n8n 或 BI 远程查询。
- 多 Agent 并发写入。
- 权限、登录、API 和长期集中数据服务。

实现时应使用 storage adapter 边界：

```text
Storage
  -> SQLiteStorage
  -> later: PostgresStorage / SupabaseStorage
```

## P0 需求

### Capability: SQLite 长期事实库

Description:

新增本地 SQLite 数据库，保存抓取、解析、评分、简报和推送状态。数据库是长期事实库，JSON 和 Markdown 继续作为运行产物。

Suggested tables:

- `fetch_runs`
- `notices`
- `notice_details`
- `opportunity_cards`
- `award_results`
- `project_links`
- `buyers`
- `suppliers`
- `briefs`
- `push_events`
- `quality_reports`

Acceptance Criteria:

- Given AM 全量采集完成, when 流水线运行, then 新公告写入 SQLite 且保留原 JSON 快照路径。
- Given PM 再次采集完成, when 系统比较历史数据, then 能识别新增、已存在和待更新公告。
- Given 同一 URL 被重复抓取, when 入库执行, then 数据不会重复插入，已有记录按规则更新。
- Given 数据库文件不存在, when 首次运行, then 系统能自动初始化 schema。
- Given 数据库写入失败, when 流水线结束, then 简报不得标记为成功推送。

### Capability: 成交结果采集与解析

Description:

新增成交结果公告采集，解析中标供应商、中标金额、采购人、代理机构、公告日期、公告正文、详情 URL 等字段。

Acceptance Criteria:

- Given 成交结果栏目存在公开公告, when 采集器运行, then 输出结构化 `award_results` 数据。
- Given 成交结果详情页包含中标供应商和中标金额, when 详情解析执行, then 字段进入 `award_results`。
- Given 部分公告没有金额或供应商字段, when 质量评估执行, then 缺失字段被记录，不编造。
- Given 成交结果采集失败, when 日报生成执行, then 系统输出风险提示而不是静默失败。

### Capability: 项目生命周期关联

Description:

将采购意向、招标公告、成交结果串联为项目生命周期。第一版不要求完全准确，采用规则关联并保留置信度。

Initial matching signals:

- 标题相似度。
- 采购人一致。
- 预算或成交金额接近。
- 公告时间窗口合理。
- 地区或栏目编码一致。

Output states:

- `matched`
- `possible_match`
- `unmatched`

Acceptance Criteria:

- Given 一条成交结果与已有招标公告标题和采购人高度一致, when 生命周期关联执行, then 生成 `matched` 关联。
- Given 标题相似但采购人不同, when 生命周期关联执行, then 不得直接标记为 `matched`。
- Given 证据不足, when 生命周期关联执行, then 标记为 `possible_match` 或 `unmatched` 并说明原因。
- Given 用户询问某项目后续是否成交, when QA 查询生命周期数据, then 只回答已存证据，不推测。

### Capability: 系统健康报告

Description:

每天输出采集和流水线健康状态，避免系统“悄悄失败”。

Metrics:

- 抓取总量。
- 新增数量。
- 去重数量。
- 详情补全率。
- 采购人缺失率。
- 预算缺失率。
- 截止时间缺失率。
- 成交金额缺失率。
- 生命周期匹配率。
- A/B/C/D 分布。
- 钉钉推送状态。

Acceptance Criteria:

- Given 今日抓取量显著低于历史均值, when 健康报告生成, then 输出异常警告。
- Given 详情补全率低于阈值, when 健康报告生成, then 标记为 WARN 或 FAIL。
- Given 钉钉推送失败, when 健康报告生成, then 明确记录失败原因和待处理状态。
- Given 所有指标正常, when 健康报告生成, then 输出 PASS 状态和关键指标摘要。

## P1 需求

### Capability: 采购人画像

Description:

基于采购意向、招标公告、成交结果，为采购单位生成长期画像。

Fields:

- 采购单位名称。
- 地区。
- 历史公告数量。
- 历史成交数量。
- 累计预算。
- 累计成交金额。
- 常见采购主题。
- 常见服务类型。
- 高频中标供应商。
- 最近一次相关采购。
- 近期是否连续采购媒体/数字化项目。

Acceptance Criteria:

- Given 数据库中存在同一采购人的多条公告, when 画像生成, then 汇总该采购人的采购频率和主题。
- Given 采购人存在成交结果, when 画像生成, then 统计历史中标供应商和成交金额区间。
- Given 采购人名称存在轻微差异, when 画像生成, then 第一版可以保守分开记录，不强行合并。

### Capability: 供应商画像

Description:

基于成交结果，为供应商生成竞争情报画像。

Fields:

- 供应商名称。
- 中标次数。
- 累计中标金额。
- 常中地区。
- 常中采购人。
- 常中服务类型。
- 最近中标项目。
- 平均成交金额。

Acceptance Criteria:

- Given 成交结果中出现供应商名称, when 画像生成, then 记录该供应商中标次数和金额。
- Given 同一供应商多次中标媒体相关项目, when 简报生成, then 可进入“高频中标供应商”区块。
- Given 供应商名称疑似重名或分支机构, when 画像生成, then 保守输出原始名称，不做无证据合并。

### Capability: 价格基准初版

Description:

按服务类型统计成交金额区间，为业务报价提供参考案例。

Initial categories:

- 短视频与直播服务。
- 新媒体运营。
- 政务宣传服务。
- 舆情监测与分析。
- 融媒体平台建设。
- 网站建设。
- 数字展厅/云展馆。
- 活动策划执行。

Acceptance Criteria:

- Given 同类成交结果数量达到最小样本数, when 价格基准生成, then 输出最低、最高、中位数和样例项目。
- Given 样本数量不足, when 价格基准生成, then 标记为样本不足，不输出强结论。
- Given 用户询问某类项目成交价, when QA 查询, then 返回历史案例和样本数量。

### Capability: 历史 QA

Description:

把 QA 从 latest `opportunity_cards.json` 扩展到 SQLite 历史数据。

Supported questions:

- 最近 30 天有哪些 A/B 机会？
- 某采购人过去采购过什么媒体相关项目？
- 某供应商最近中了哪些标？
- 某项目最后谁中了？
- 哪些招标公告需要立即响应？

Acceptance Criteria:

- Given 数据库中有历史机会卡, when 用户问最近 30 天 A/B 机会, then 返回时间范围内的项目列表。
- Given 用户问未披露字段, when QA 回答, then 明确说明数据中没有该字段。
- Given 用户要求报名、投标、提交材料, when QA 回答, then 拒绝执行并转为情报建议。

## P2 需求

### Capability: 赛道月报

Description:

按业务赛道输出月度趋势，用于管理层判断市场需求变化。

Candidate tracks:

- 政务宣传服务。
- 文旅宣传推广。
- 短视频与直播服务。
- 新媒体矩阵运营。
- 融媒体平台建设。
- 舆情监测与分析。
- 数字展厅/云展馆。
- AI 数字人/AIGC 内容生产。
- 数据治理与知识库建设。
- 活动策划执行。
- 城市品牌传播。

Acceptance Criteria:

- Given 数据库中存在一个月以上数据, when 月报生成, then 输出各赛道项目数、预算、成交金额和重点采购人。
- Given 某赛道样本不足, when 月报生成, then 标记样本不足。

### Capability: 产品包反推

Description:

基于成交结果和高频采购主题，识别可产品化方向，例如文旅新媒体增长包、城市品牌短视频包、政务账号年度运营包等。

Acceptance Criteria:

- Given 某类需求在多个地区重复出现, when 产品包分析执行, then 输出候选产品包、证据项目和预算区间。
- Given 证据不足, when 产品包分析执行, then 不输出确定性建议。

### Capability: 评分复盘

Description:

使用成交结果反向检查过去 A/B/C/D 评分是否有效。

Acceptance Criteria:

- Given 已评分机会后来产生成交结果, when 复盘执行, then 记录原评分、成交结果和命中状态。
- Given A/B 机会长期没有后续结果, when 复盘执行, then 标记为待观察，不直接判定误判。

## 暂不纳入近期范围

### 完整业务待办系统

暂不做完整状态流转、负责人分派、钉钉互动按钮和漏斗管理。第一阶段可以只记录 `push_events` 和人工备注字段，为后续任务流打基础。

### 赢面预测

没有内部 CRM、历史跟进记录、报价记录和投标结果前，不做赢面预测。可先做“跟进优先级”和“风险提示”。

### 审计化风险判断

系统可以提示经营风险，例如“竞争壁垒可能较高”“截止时间过近”“更正公告频繁”。不得输出“疑似围标”“疑似内定”等审计判断。

### 复杂图谱和 BI

第一阶段只做表格、JSON、Markdown 和 QA。Web 看板、图谱可视化、BI 查询等在数据沉淀和使用场景明确后再做。

## 推荐实施顺序

### Phase 1: 存储底座

1. 已新增 SQLite storage adapter。
2. 已建立首版 schema：`fetch_runs`、`notices`、`notice_details`、`opportunity_cards`、`push_events`、`quality_reports`。
3. 已支持小时级采集快照入库和 URL 去重。
4. 已支持 AM/PM 简报从 SQLite 读取，避免简报时间点实时全量抓取。
5. 仍保留 JSON/Markdown 输出，用于可观测性、人工复核和回放。

Runtime commands:

```bash
python3 scripts/run_hourly_collection.py --today <date> --hour <HH> --db-path data/procurement_intel.db
python3 scripts/run_brief_from_db.py --mode am --today <date> --db-path data/procurement_intel.db --output-dir reports/<date>/am
python3 scripts/run_brief_from_db.py --mode pm --today <date> --since-brief am --db-path data/procurement_intel.db --output-dir reports/<date>/pm
```

Operational rule:

```text
小时任务负责采集和入库；AM/PM 简报任务只读 SQLite，不启动浏览器抓取。
```

### Phase 2: 成交结果

1. 新增成交结果采集目标。
2. 解析成交供应商、成交金额、采购人、代理机构和正文。
3. 增加成交结果质量评估。
4. 成交结果入库。

### Phase 3: 生命周期

1. 实现规则关联。
2. 输出 `project_lifecycle_cards.json`。
3. 简报增加成交跟踪区块。
4. QA 支持项目后续查询。

### Phase 4: 画像和价格基准

1. 生成采购人画像。
2. 生成供应商画像。
3. 生成服务类型价格基准。
4. 钉钉简报增加高频采购人和高频供应商摘要。

### Phase 5: 历史 QA 和复盘

1. QA 从 SQLite 读取历史数据。
2. 支持固定经营问题。
3. 使用成交结果做评分复盘。
4. 形成周报/月报基础。

## 建议新增产物

```text
runtime_data/
  procurement_intel.db
  snapshots/
  reports/

reports/<date>/
  award_results.json
  project_lifecycle_cards.json
  buyer_supplier_insights.md
  system_health_report.json
```

开发仓库中 `runtime_data/` 和 `reports/` 应默认忽略，不进入 GitHub，除非明确作为公开 fixture。

## 数据质量规则

所有新能力必须遵守：

- 不用测试通过代替真实质量。
- 不用抓取数量代替字段完整性。
- 不编造未披露字段。
- 每条推断保留证据或置信度。
- 对关联结果区分 `matched`、`possible_match`、`unmatched`。
- 对样本不足的统计明确标注样本量。

## Notes for Codex

后续实现前必须：

1. 运行 `git pull --ff-only origin main`。
2. 阅读 `AGENTS.md`、`docs/project_spec.md`、`docs/openclaw-contract.md` 和本文档。
3. 不修改 `~/.openclaw/`。
4. 不执行真实部署，除非用户明确要求。
5. 不引入 Supabase 作为第一阶段强依赖。
6. 保持 SQLite storage adapter 可迁移到 Postgres/Supabase。
7. 运行 `bash scripts/validate.sh`。
8. 如果修改运行服务器代码路径，确保运行服务器侧变更回传 GitHub 后再继续开发。

Suggested first task:

```text
继续完成 SQLite 小时级采集计划中的健康报告、部署 dry-run 清单更新和 runtime 切换 runbook。
```

## 已制定实施计划

SQLite 小时级持续采集和 AM/PM 从库生成简报的实施计划已保存到：

```text
docs/superpowers/plans/2026-06-10-sqlite-hourly-collection.md
```

该计划将第一阶段限定为：

- SQLite 本地事实库。
- 每小时采集并入库。
- 已知 URL 跳过详情补全。
- AM/PM 简报从 SQLite 读取，不实时抓取。
- 系统健康报告。

成交结果采集、生命周期关联、采购人画像和供应商画像应在该计划完成并稳定运行后进入下一轮计划。
