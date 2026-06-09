# 政采情报库（MVP）- 温州媒体业务专项

## 0. 项目目标与边界

### 0.1 目标（MVP）

构建一个自动化系统：每天抓取中国政府采购网温州市公开招标公告，筛选媒体业务相关项目，结构化成"项目卡"，支持导出与推送。

**MVP 必须实现：**
1. 定时抓取温州市公开招标公告列表并增量入库（不漏、不重复）
2. 解析公告详情，抽取关键字段（预算、截止、采购方式、采购人、代理等）
3. 媒体业务分类与关键词过滤
4. 项目导出（JSON/CSV）
5. 推送通知（Discord Webhook）

### 0.2 非目标（MVP 不做）
- 不做登录态数据抓取
- 不做中标结果回填
- 不做 PDF 附件解析
- 不做复杂前端

### 0.3 合规与伦理边界
- 仅抓取"公开可访问"的公告页面
- 不采集个人敏感信息（身份证、手机号等）

---

## 1. 技术选型

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| 编排层 | Python + Cron | 轻量替代 n8n |
| 数据层 | SQLite | MVP 阶段够用，后续可迁移 Supabase |
| 解析层 | requests + BeautifulSoup4 | 直接解析 HTML |
| 推送层 | Discord Webhook | 已配置 |

---

## 2. 数据库设计

### 表结构

```sql
-- sources: 数据源配置
CREATE TABLE sources (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    region TEXT DEFAULT '温州',
    notice_type TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- notices: 公告原始表
CREATE TABLE notices (
    id INTEGER PRIMARY KEY,
    notice_url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id),
    region TEXT,
    publish_date DATE,
    notice_type TEXT,
    status TEXT DEFAULT 'new',
    raw_html TEXT,
    error_reason TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- projects: 项目聚合表（媒体业务相关）
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    notice_id INTEGER REFERENCES notices(id),
    project_key TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    buyer TEXT,
    budget_amount DECIMAL(15,2),
    deadline_at TIMESTAMP,
    proc_method TEXT,
    agent TEXT,
    category TEXT,
    tags JSONB DEFAULT '[]',
    risk_flags JSONB DEFAULT '[]',
    match_score INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- subscriptions: 订阅规则
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    region TEXT,
    category TEXT,
    keywords TEXT,
    min_budget DECIMAL(15,2),
    enabled INTEGER DEFAULT 1,
    webhook_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_notices_status ON notices(status);
CREATE INDEX idx_notices_region ON notices(region);
CREATE INDEX idx_notices_publish_date ON notices(publish_date);
CREATE INDEX idx_projects_category ON projects(category);
CREATE INDEX idx_projects_status ON projects(status);
```

---

## 3. 关键词过滤规则

### 媒体业务关键词库

```python
MEDIA_KEYWORDS = [
    # 广告类
    "广告制作", "标识标牌", "喷绘", "展板", "海报", "灯箱", "物料", "制作服务",
    # 视频类
    "宣传片", "专题片", "视频拍摄", "摄影", "剪辑", "后期制作", "短视频", "视频制作",
    # 融媒类
    "融媒体", "媒资", "采编", "CMS", "小程序", "直播系统", "非编", "转码", "字幕",
    # 传播类
    "舆情监测", "传播服务", "数据分析", "账号运营", "媒体投放", "新媒体运营",
    # 其他
    "文化创意", "活动策划", "展览展示", "舞美", "公关", "品牌策划"
]
```

### 风险标红规则

```python
RISK_FLAGS = [
    ("截止临期", lambda d: d and (d - now).total_seconds() < 72*3600),
    ("预算低于5万", lambda b: b and b < 50000),
]
```

---

## 4. 数据源 URL

### 温州市公告列表

| 类型 | URL |
|------|-----|
| 公开招标 | http://www.ccgp.gov.cn/cggg/dfgg/gkzb/ |
| 中标结果 | http://www.ccgp.gov.cn/cggg/dfgg/zbgg/ |
| 更正公告 | http://www.ccgp.gov.cn/cggg/dfgg/gzgg/ |

**注意**：需在列表页筛选温州市，或在详情页根据"行政区域"字段过滤。

---

## 5. 项目结构

```
政采情报库/
├── config.py                 # 配置（数据库路径、Webhook URL 等）
├── db.py                    # 数据库操作
├── fetcher.py               # 抓取公告列表
├── parser.py                # 解析公告详情
├── notifier.py              # 推送通知
├── scheduler.py             # 定时任务
├── media_filter.py          # 媒体业务过滤
├── main.py                  # 入口
├── requirements.txt
├── data/
│   └── govproc.db           # SQLite 数据库
├── scripts/
│   ├── init_db.py           # 初始化数据库
│   ├── seed_sources.py      # 种子数据
│   └── export_projects.py   # 导出项目
└── tests/
    └── test_parser.py       # 测试
```

---

## 6. 核心接口

### fetcher.py

```python
def fetch_notice_list(source_id: int, page: int = 1) -> List[dict]:
    """抓取公告列表页"""
    pass

def fetch_notice_detail(notice_url: str) -> dict:
    """抓取公告详情页"""
    pass
```

### parser.py

```python
def parse_notice_detail(html: str, url: str) -> dict:
    """解析公告详情，抽取字段"""
    # 抽取：title, buyer, budget_amount, deadline_at, proc_method, agent, region
    pass
```

### media_filter.py

```python
def is_media_related(title: str, content: str = "") -> tuple[bool, list[str]]:
    """判断是否媒体业务相关，返回 (是否匹配, 匹配的关键词)"""
    pass
```

---

## 7. 定时任务

```python
# 每日 06:00 执行
@scheduler.scheduled_job("cron", hour=6, minute=0)
def job_daily_fetch():
    # 1. 抓取公告列表
    # 2. 解析详情
    # 3. 过滤媒体业务
    # 4. 导出 + 推送
    pass
```

---

## 8. 环境变量

```bash
# .env
DISCORD_WEBHOOK_URL=<set in local environment only>
DATABASE_PATH=./data/govproc.db
LOG_LEVEL=INFO
FETCH_TIMEOUT=30
MAX_RETRY=3
```

---

## 9. 验收标准

- [ ] 本地运行 `python main.py` 能抓取当天公告
- [ ] 增量入库，无重复
- [ ] 媒体业务关键词过滤生效
- [ ] 能导出 JSON/CSV
- [ ] Discord Webhook 推送成功

---

## 10. 实施优先级

| 优先级 | 任务 | 预计工时 |
|--------|------|---------|
| P0 | 数据库 + 抓取脚本 | 2h |
| P0 | 解析 + 过滤 | 2h |
| P0 | 导出 + 推送 | 1h |
| P1 | 定时任务 | 1h |
| P1 | 测试 + 优化 | 2h |

**MVP 预计总工时：8 小时**

---

*版本: v1.0 | 创建: 2026-02-14*
