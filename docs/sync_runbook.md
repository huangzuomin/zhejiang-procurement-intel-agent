# Sync Runbook: PR 合并后智能体同步更新

> 当 feature 分支 PR 合并到 main 后，生产环境的 OpenClaw 智能体如何同步代码并验证。

## 适用场景

开发环境完成迭代 → 提交 PR → Code Review → 合并到 main → **通知生产环境 agent 同步**。

## 同步流程（6 步）

### Step 1: 拉取最新代码

```bash
cd /home/ai/.config/superpowers/worktrees/zhejiang-procurement-intel-agent/sqlite-hourly-collection

# 切到 main，拉取合并后的代码
git checkout main
git pull --ff-only origin main
```

### Step 2: 安装依赖

```bash
# Node 依赖（puppeteer 等）
PUPPETEER_SKIP_DOWNLOAD=1 npm install

# Python 依赖（如有变更）
pip install -r requirements.txt -q 2>/dev/null || true
```

**检查点**：
- `node -e "require('puppeteer')"` 不报错
- `python3 -c "from procurement_intel import storage"` 不报错

### Step 3: 回切到最新的 feature worktree

如果 main 合并后需要继续开发，保持 worktree 在 main 即可：

```bash
# 如果继续开发新功能，切回 feature 分支并 rebase
git checkout -b feature/<新功能名> origin/main
# 或直接在 main 上跑生产
```

**当前生产路径**：`/home/ai/.config/superpowers/worktrees/zhejiang-procurement-intel-agent/sqlite-hourly-collection`

### Step 4: 运行测试

```bash
python3 -m pytest tests/ -x --tb=short
bash scripts/validate.sh
python3 scripts/prepare_deploy_dry_run.py --json
```

**通过标准**：
- 全部 test case 通过
- `forbidden_matches` 为 `[]`
- 无 runtime data / secrets 被提交

### Step 5: Smoke Test（如涉及以下变更则必须执行）

涉及范围：
- 采集脚本（zfcg_browser_scraper.js, run_hourly_collection.py）
- SQLite schema（storage.py）
- 简报逻辑（db_briefing.py, run_brief_from_db.py）
- 评分/分类（scorer.py, classifier.py）
- 推送格式
- 定时任务命令

```bash
TODAY=$(date +%F)
HOUR=$(date +%H)
DB=data/procurement_intel.db

# 1. 小时采集（限 5 条）
PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome \
  python3 scripts/run_hourly_collection.py \
  --today "$TODAY" --hour "$HOUR" \
  --db-path "$DB" --limit 5 --detail-limit 5 --json

# 2. 重复运行（验证幂等）
PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome \
  python3 scripts/run_hourly_collection.py \
  --today "$TODAY" --hour "$HOUR" \
  --db-path "$DB" --limit 5 --detail-limit 5 --json

# 验证：known_url_count > 0, new_count = 0

# 3. AM 简报
python3 scripts/run_brief_from_db.py \
  --mode am --today "$TODAY" --db-path "$DB" \
  --output-dir "reports/$TODAY/am"

# 4. PM 简报
python3 scripts/run_brief_from_db.py \
  --mode pm --today "$TODAY" --since-brief am \
  --db-path "$DB" --output-dir "reports/$TODAY/pm"

# 5. 健康报告
python3 scripts/run_health_report.py \
  --today "$TODAY" --db-path "$DB" \
  --output "reports/$TODAY/health_report.json" --json
```

### Step 6: 更新 Cron 任务（如涉及）

如果变更影响了：
- 工作目录路径
- 命令行参数
- 环境变量（如 `PUPPETEER_EXECUTABLE_PATH`）
- 新增/删除了定时任务

则通过 `cron update` 更新对应的 job payload。

**当前 Cron Job 清单**：

| Job ID | 名称 | Schedule |
|--------|------|----------|
| `8210ac7b` | 政采-hourly-collection | `5 8-18 * * *` |
| `8c9dbd11` | 政采-am-brief | `20 9 * * *` |
| `8c91caf8` | 政采-pm-brief | `20 15 * * *` |
| `eaefaacb` | 政采-health-report | `30 18 * * *` |

## 同步检查清单

每次同步后，按此清单逐项确认：

```
[ ] 1. git pull 成功，无冲突
[ ] 2. npm install 成功
[ ] 3. pytest 全部通过
[ ] 4. validate.sh 通过
[ ] 5. dry-run 通过（无 forbidden matches）
[ ] 6. Smoke: 第一次 hourly collection 成功
[ ] 7. Smoke: 第二次 hourly collection 幂等（new=0）
[ ] 8. Smoke: 已有数据不退化（buyer/budget/deadline/grade）
[ ] 9. Smoke: AM brief 生成成功
[ ] 10. Smoke: PM brief 生成成功
[ ] 11. Smoke: health report PASS
[ ] 12. Cron 任务路径/参数正确（如无变更则跳过）
[ ] 13. 记录到 docs/deploy_log.md
```

## 快速同步（仅代码修复，无 schema/行为变更）

如果只是 bug fix，不涉及 schema、采集逻辑、简报格式：

```bash
cd /home/ai/.config/superpowers/worktrees/zhejiang-procurement-intel-agent/sqlite-hourly-collection
git checkout main && git pull --ff-only origin main
python3 -m pytest tests/ -x --tb=short
# 通过即完成
```

## 回滚

```bash
# 回到上一个已知好的 tag
git tag -l 'v*' --sort=-version:refname | head -3  # 查看最近 tag
git checkout <上一个tag>
python3 -m pytest tests/ -x --tb=short
```

回滚后必须记录到 `docs/deploy_log.md`。

## 注意事项

- **不要**在生产 worktree 里直接开发，开发在独立的 feature 分支进行
- **不要**提交 `data/`、`reports/`、`node_modules/` 到 Git
- **不要**在 AM/PM 简报任务里启动浏览器抓取
- **不要**硬编码钉钉 token/webhook
- 浏览器抓取**只**由 hourly-collection 任务执行
- 首日 bootstrap/backfill **必须**单独执行，不混入定时任务
- 所有 runtime 数据写入 `data/` 和 `reports/`

---

*版本: v1.0 | 创建: 2026-06-10 | 维护者: 璇玑*
