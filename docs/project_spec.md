# Project Spec: 政采情报库 Agent

## Goal

将现有“政采情报库”重构为 OpenClaw 原生 Agent 应用，面向文字新闻网业务部门自动监测浙江政府采购网公告，发现适合媒体业务参与的项目，并在钉钉群中提供可行动的项目简报、机会研判和基于已采集公告的问答。

第一版只覆盖：情报发现、项目研判、每日/每周简报、群内问答。成交历史深度分析保留为后续能力，不进入第一版交付范围。

## Artifact Type

OpenClaw sub-agent workspace with internal Skills.

Justification:

- 该系统需要持续角色、长期偏好、固定职责边界和群聊交互，不适合只做一次性 Skill。
- Agent 是产品主体，负责判断、解释、追问和简报生成。
- 采集、解析、评分、简报、问答应作为 Agent 可调用的工具链和内部 Skills。

## Recommended Architecture

```text
openclaw/agent/
  AGENTS.md
  IDENTITY.md
  SOUL.md
  TOOLS.md
  USER.md
  skills/
    daily_procurement_brief/
    notice_opportunity_eval/
    procurement_qa/
    keyword_strategy_tuning/
  resources/
    media_business_taxonomy.md
    scoring_rules.md
    risk_rules.md
    dingtalk_message_format.md

app/
  collectors/
  parsers/
  classifier/
  scorer/
  briefing/
  dingtalk/
  storage/
  scripts/

tests/
  unit/
  fixtures/
  integration/
```

Agent 层负责 OpenClaw 原生交互、身份、策略、问答边界和输出标准。`app/` 层只负责可测试的数据采集、结构化、评分、存储和钉钉适配，不承载产品身份。

## Target User

文字新闻网业务部门工作人员，包括负责业务拓展、项目跟进、内容服务、新媒体运营、视频业务、网站建设和信息化项目沟通的人员。

## User Scenario

- 每天早上，Agent 在钉钉群推送浙江政府采购网媒体业务机会简报。
- 当出现高匹配度或临期重要机会时，Agent 在钉钉群推送即时提醒。
- 业务人员在群里追问单个项目是否值得跟进、风险在哪里、适合什么业务切入点、是否有类似历史线索。
- 每周，Agent 汇总本周机会、重点采购人、项目类别分布和下周待关注事项。

## Input

- 浙江政府采购网公开可访问的公告列表页和详情页。
- 第一版关注公告类型：招标公告、采购意向。成交公告仅作为后续历史分析输入预留。
- 旧版 `SPEC.md` 中的媒体业务关键词与风险规则。
- 用户后续提供的媒体业务偏好、排除规则、预算阈值、地区优先级和钉钉群配置。
- 群聊中的用户追问，限定在已采集公告、项目研判和简报解释范围内。

## Output

### Project Opportunity Card

每个值得看的项目输出统一机会卡：

- 项目标题
- 公告 URL
- 公告类型
- 发布时间
- 地区
- 采购人
- 预算
- 截止时间
- 匹配类别
- 机会等级：A 类重点跟进、B 类值得关注、C 类边缘机会、D 类排除
- 匹配理由
- 主要风险
- 推荐动作

### DingTalk Brief

钉钉每日简报包含：

- 今日新增公告数量
- 值得看的机会数量
- A/B 类重点项目列表
- 临期项目提醒
- 低价值或排除项目摘要
- 可追问提示，例如“回复项目序号了解风险和跟进建议”

### Conversational Answer

群内问答回答应：

- 基于已采集公告和规则，不编造外部事实。
- 给出明确结论、证据、风险和下一步建议。
- 对不确定信息说明“不确定原因”和可补充材料。

## Workflow

1. 定时或手动触发公告采集。
2. 获取浙江政府采购网公告列表和详情页。
3. 去重并保存原始公告、结构化字段和抓取状态。
4. 对公告进行媒体业务分类和机会评分。
5. 生成项目机会卡。
6. 选择 A/B 类项目进入简报或即时提醒。
7. 将简报推送到钉钉群。
8. 接收群内追问，检索相关公告和机会卡。
9. 生成项目解释、风险研判或简短跟进建议。
10. 记录用户反馈，用于后续关键词和评分规则调整。

## Core Capabilities

### Capability: 浙江政府采购公告监测

Description:

监测浙江政府采购网公开公告，抓取公告列表和详情，保存原始 HTML、结构化字段和抓取状态。

Acceptance Criteria:

- Given 浙江政府采购网可访问, when 监测任务运行, then 系统保存新增公告并跳过已存在 URL。
- Given 公告详情页抓取失败, when 监测任务运行, then 系统记录失败原因和重试状态，不中断整个任务。
- Given 公告内容为空或页面结构变化, when 解析失败, then 系统保留原始抓取记录并标记为需人工检查。

### Capability: 媒体业务机会识别

Description:

判断公告是否适合媒体业务参与，并分类为信息化建设、网站建设、新媒体运营与运维、视频拍摄、GEO 类项目、融媒体/传播服务、广告制作、活动策划或其他。

Acceptance Criteria:

- Given 公告包含“新媒体运营”“视频拍摄”“网站建设”等明确业务词, when 机会识别运行, then 系统输出匹配类别和命中证据。
- Given 公告只包含宽泛“信息化建设”, when 无媒体相关子项, then 系统标记为边缘机会或排除，并解释原因。
- Given 公告同时命中多个类别, when 评分运行, then 系统输出主类别、次类别和排序理由。

### Capability: 项目机会评分与风险研判

Description:

根据业务适配度、商务价值、紧急程度和风险信号生成 A/B/C/D 机会等级。

Acceptance Criteria:

- Given 公告明确包含媒体业务、预算合理、截止时间充足, when 评分运行, then 系统输出 A 或 B 类机会及推荐动作。
- Given 公告预算过低、截止临近或资质门槛强, when 评分运行, then 系统输出风险标签并降低机会等级。
- Given 信息不足, when 评分运行, then 系统输出保守等级和缺失字段，不伪造结论。

### Capability: 钉钉项目简报

Description:

将当天或本周机会整理为适合钉钉群阅读的简报。

Acceptance Criteria:

- Given 当天存在 A/B 类机会, when 每日简报生成, then 钉钉消息包含重点项目、理由、风险和追问入口。
- Given 当天没有值得看的项目, when 每日简报生成, then 钉钉消息说明无重点机会并给出监测范围。
- Given 消息过长, when 简报生成, then 系统优先保留 A 类机会并压缩 C/D 类摘要。

### Capability: 群内项目问答

Description:

业务人员可以在钉钉群中围绕已采集公告询问项目价值、风险、切入点和简报解释。

Acceptance Criteria:

- Given 用户询问“这个项目适合我们投吗”, when 能定位到公告, then Agent 输出结论、证据、风险和建议动作。
- Given 用户问题超出政采情报范围, when Agent 回复, then Agent 礼貌拒绝或引导回公告、项目和简报问题。
- Given 用户引用模糊项目, when 多个候选公告匹配, then Agent 请求用户选择项目或提供更具体信息。

### Capability: 规则与偏好沉淀

Description:

记录用户对机会判断的反馈，为后续规则调优提供依据。第一版只记录，不自动大幅修改核心规则。

Acceptance Criteria:

- Given 用户在群内指出某类项目不适合, when Agent 记录反馈, then 系统保存反馈类型、关联公告和建议规则。
- Given 新规则可能影响大量判断, when 用户提出调整, then Agent 提示需要确认后再应用。

## Non-goals

- 第一版不做自动报名、投标文件生成或投标流程执行。
- 第一版不做登录态、验证码绕过或非公开数据采集。
- 第一版不做 PDF 附件深度解析。
- 第一版不做完整前端后台。
- 第一版不做成交历史深度预测，只预留数据结构和后续 Skill。
- 第一版不让 Agent 代替业务人员作最终投标决策。

## Acceptance Criteria

- Agent 能以“政采情报官”身份在 OpenClaw 中被清晰识别。
- 本地验证命令 `bash scripts/validate.sh` 通过。
- 至少有 fixtures 覆盖网站建设、新媒体运营、视频拍摄、信息化边缘项目、GEO 类项目和无关项目。
- 钉钉简报格式稳定，能包含 A/B 类机会和追问入口。
- 群内问答只基于已采集数据和规则作答，不编造未采集事实。
- 部署前 delivery audit 结果为 PASS，或 PASS_WITH_WARNINGS 后由用户明确批准。

## Risks and Mitigations

- 浙江政府采购网页面结构变化：保存原始 HTML，解析失败时保留原始记录和错误状态。
- “信息化建设”误报较多：将其设为边缘机会类，要求媒体相关子项或语义证据才能升为 A/B。
- GEO 类项目定义新且边界模糊：建立独立词表和人工反馈机制，第一版保守评分。
- 钉钉群问答可能被问到执行类问题：Agent 边界限定为情报、研判、简报和解释。
- 采集触发外部网站限流：控制请求频率，记录失败，不绕过反爬或登录限制。
- 历史数据库污染部署包：运行态数据不得进入 OpenClaw runtime artifact。

## Dependencies

- 浙江政府采购网公开页面可访问。
- 钉钉机器人或群聊接入方式由用户确认。
- 本地持久化存储，第一版建议 SQLite 或等价轻量数据库。
- Python/Node 采集工具链可以作为实现选择，但不作为 Agent 身份的一部分。
- OpenClaw runtime 目标路径和部署流程需在部署前确认。

## Assumptions

- 项目名称暂定为“政采情报库 Agent”。
- Agent 名称暂定为 `zhejiang_procurement_intel_agent`。
- 第一版覆盖浙江政府采购网，地区以浙江全省为范围，不再只限温州。
- 钉钉群是主要交互入口。
- 第一版允许写入项目本地数据目录和日志，但不允许直接写 OpenClaw runtime。
- 第一版推荐每天早晨生成简报，重要机会可即时提醒，具体时间由用户后续配置。

## Open Questions

- 钉钉接入方式、群机器人密钥和消息回调机制由谁提供。
- 第一版是否需要只推送 A/B 类项目，还是也展示 C 类边缘机会摘要。
- 预算阈值、地区优先级和采购人黑白名单尚未确认。
- GEO 类项目的正式定义、关键词和典型案例需要用户补充。
- OpenClaw runtime target 最终路径需要部署前确认。

## Implementation Hints for Codex

Recommended task sequence:

1. Create `openclaw/agent/AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `TOOLS.md`, and `USER.md`.
2. Add agent resources: `media_business_taxonomy.md`, `scoring_rules.md`, `risk_rules.md`, and `dingtalk_message_format.md`.
3. Build the app tool layer around collectors, parsers, classifier, scorer, briefing, dingtalk, and storage modules.
4. Add fixtures and tests before implementing each classifier/scorer behavior.
5. Add `scripts/validate.sh`.
6. Run `bash scripts/validate.sh`.
7. Report files changed and validation result.

Complexity:

- High

Dependencies:

- DingTalk integration details.
- Stable sample pages or fixtures from Zhejiang Government Procurement.
- Confirmed runtime target before deployment.

Suggested first task:

- Scaffold the OpenClaw agent identity and resources, then implement test fixtures for opportunity classification before writing live collectors.

## Notes for Codex

- Read these files first: `docs/project_spec.md`, `docs/openclaw-contract.md`, `docs/test_plan.md`, `docs/deploy_manifest.md`, `SPEC.md`.
- Edit these files: `openclaw/agent/*`, `openclaw/agent/skills/*`, `openclaw/agent/resources/*`, `app/*`, `tests/*`, `scripts/validate.sh`.
- Do not edit these files: `.venv/`, `venv/`, `node_modules/`, `__pycache__/`, `data/govproc.db`, OpenClaw runtime directories.
- Code writing allowed: Yes, after user approves this document set.
- Deployment allowed: No, not until delivery audit passes and user explicitly requests deployment.
- Validation commands: `bash scripts/validate.sh`, `git status`, `git diff`.
- Do not deploy without delivery audit.
- Do not deploy without `docs/deploy_manifest.md`.
- Do not manually copy files into `~/.openclaw`.
- Do not invent OpenClaw CLI commands.
- Deployment must be handled by the approved deployment workflow or `openclaw_internal_deployer` Skill.
- Run `bash scripts/validate.sh` before finishing implementation.
- Report files changed, commands run, validation result, and anything not validated.
