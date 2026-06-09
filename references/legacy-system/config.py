"""配置管理"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# 数据库
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "govproc.db"))

# 抓取配置
FETCH_TIMEOUT = int(os.getenv("FETCH_TIMEOUT", "30"))
MAX_RETRY = int(os.getenv("MAX_RETRY", "3"))
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Discord Webhook
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# 日志
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# 媒体业务关键词
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

# 目标地域
TARGET_REGIONS = ["温州", "温州市"]

# 数据源配置
SOURCES = [
    {
        "name": "温州市公开招标",
        "base_url": "http://www.ccgp.gov.cn/cggg/dfgg/gkzb/",
        "region": "温州",
        "notice_type": "tender"
    },
    {
        "name": "温州市中标结果",
        "base_url": "http://www.ccgp.gov.cn/cggg/dfgg/zbgg/",
        "region": "温州",
        "notice_type": "award"
    },
    {
        "name": "温州市更正公告",
        "base_url": "http://www.ccgp.gov.cn/cggg/dfgg/gzgg/",
        "region": "温州",
        "notice_type": "correction"
    }
]
