# MEMORY.md - 政采情报库 Agent 运行经验

## 2026-06-09 全量+增量采集测试

### 浏览器抓取经验

**1. 日期筛选 ref 不可靠，每次页面导航/标签重建后 ref 会变**
- 采购意向公开页：日期筛选 input ref 随 snapshot 变化
- 招标公告页：日期筛选 ref 也不同
- 做法：每次操作前先 snapshot 获取最新 ref，或用 JS evaluate 按属性/placeholder 查找

**2. 浏览器翻页后 window 变量数据会丢失**
- `window._bidAll` 在翻页结束后可读，但如果页面导航到其他栏目则数据清空
- 如果 CDP 连接断开或浏览器重启，所有内存数据丢失
- 教训：翻页抓取后应立即持久化，不要依赖内存

**3. 浏览器 fetch 无法 POST 到 localhost（CORS + mixed content）**
- HTTPS 页面不能 fetch 到 HTTP localhost
- 自签名 HTTPS 也不行（浏览器拒绝）
- ✅ 正确方案：用 **CDP WebSocket** 直连浏览器执行 evaluate，Node.js 脚本 `cdp_scrape_bids.js` 已验证可行
- CDP HTTP endpoint: `http://127.0.0.1:18800/json` 获取所有 tab 的 wsUrl

**4. evaluate 超长 JS 字符串会被截断导致 "Unexpected end of input"**
- 翻页逻辑如果写成单个 evaluate 字符串超过约 800 字符可能被截断
- 做法：先 `evaluate` 注入短函数到 `window`，再分步调用
- 或者用 CDP Node.js 脚本直接通过 WebSocket 执行（无截断限制）

**5. 子任务上下文溢出是主要风险**
- 全流程 spawn 子任务在 glm-5-turbo 上下文约 10 分钟后溢出
- 教训：大流程应拆分为多个独立子任务（抓取 → pipeline → 发送），或用更大上下文模型
- 当前可用方案：在主会话分步执行，或每个子任务只做一步

### Pipeline 脚本经验

**6. `full_collect_and_brief.js` AM/PM 模式工作正常**
- AM: 读 intentions + bids → detail API 补全 → 分类评分 → 生成简报 → 备份 snapshot
- PM: 同上 + URL 去重对比 AM snapshot → 标注新增
- 454 条补全约 2-3 分钟（31 批 × 15条/批）
- 详情 API: `https://zfcg.czt.zj.gov.cn/portal/detail?articleId={id}&timestamp={ts}`

**7. 数据格式约定**
- `data/latest_intentions.json`: `[{region, category, title, url, date}]` 纯数组
- `data/latest_bids.json`: 同上格式纯数组
- 子任务可能写成 `{source, date, items: [...]}` 格式，pipeline 只读纯数组，需要转换

### 钉钉发送经验

**8. 钉钉群消息限约 20000 字符**
- 195 条截止提醒原文超 30000 字符，必须精简
- 做法：A/B 类全量 + 统计表 + 截止提醒只列前 20 条 + 提示总数
- accountId: `zhejiang_procurement`, target: `cid3eI/7oNrlJfnFadwzoQitw==`

### 架构决策

**9. CDP 脚本是浏览器抓取的最佳持久化方案**
- `scripts/cdp_scrape_bids.js`: 通过 CDP WebSocket 连接浏览器，自动翻页抓取并保存到文件
- 优点：无 CORS 限制、无字符串截断、数据直接写文件
- 缺点：需要浏览器保持打开
- 建议：将采购意向抓取也改用同样 CDP 脚本方式，统一为 `cdp_scrape_all.js`

**10. 理想的自动化流程**
1. `node scripts/cdp_scrape_all.js --date 2026-06-09` → 保存 intentions + bids
2. `node scripts/full_collect_and_brief.js --mode am --today 2026-06-09` → 补全+分类+简报
3. 读取 brief → `message` 发钉钉
4. PM 同样流程，自动 diff
5. 全流程可用 cron 定时执行（如每日 9:00 AM + 14:00 PM）

## 2026-06-10 SQLite 小时级采集升级

### 运行经验

**11. 高数据量场景不要在简报时间点实时全量抓取**
- 454 条级别的全量抓取、详情补全、分类和简报生成放在同一个 AM/PM 任务里容易超时
- 正确路径：每小时采集并入库，AM/PM 简报只读 SQLite
- 小时入口：`python3 scripts/run_hourly_collection.py --today <date> --hour <HH> --db-path data/procurement_intel.db`
- AM 入口：`python3 scripts/run_brief_from_db.py --mode am --today <date> --db-path data/procurement_intel.db --output-dir reports/<date>/am`
- PM 入口：`python3 scripts/run_brief_from_db.py --mode pm --today <date> --since-brief am --db-path data/procurement_intel.db --output-dir reports/<date>/pm`

**12. SQLite 是当前 runtime 的事实库**
- `data/procurement_intel.db` 保存 notices、opportunity_cards、fetch_runs、push_events、quality_reports
- `data/snapshots/<date>/<hour>.json` 是可回放证据，不是主状态
- 已知 URL 会写入 `data/runtime/<date>/known_urls.txt`，采集器据此跳过重复详情补全
- 健康入口：`python3 scripts/run_health_report.py --today <date> --db-path data/procurement_intel.db --output reports/<date>/health_report.json`

**13. 旧实时流水线只作为回滚方案**
- `scripts/full_collect_and_brief.js` 和 live JSON -> `run_daily_pipeline.py` 仍可用
- SQLite cutover 后默认不要用旧实时流水线做高量定时任务
- 如果 SQLite 健康报告 FAIL，可临时回滚到 live JSON 流程，但要保留失败快照和错误信息
