"""媒体业务过滤器"""
import re
from typing import List, Tuple
import config


def is_media_related(title: str, content: str = "") -> Tuple[bool, List[str]]:
    """
    判断是否媒体业务相关
    返回: (是否匹配, 匹配的关键词列表)
    """
    if not title:
        return False, []
    
    text = f"{title} {content}".lower()
    matched = []
    
    for keyword in config.MEDIA_KEYWORDS:
        if keyword.lower() in text:
            matched.append(keyword)
    
    return len(matched) > 0, matched


def categorize_media(matched_keywords: List[str]) -> str:
    """
    根据匹配的关键词对媒体业务进行分类
    """
    if not matched_keywords:
        return "其他"
    
    # 定义分类规则
    categories = {
        "广告制作": [
            "广告制作", "标识标牌", "喷绘", "展板", "海报", "灯箱", "物料", "制作服务"
        ],
        "视频制作": [
            "宣传片", "专题片", "视频拍摄", "摄影", "剪辑", "后期制作", "短视频", "视频制作"
        ],
        "融媒系统": [
            "融媒体", "媒资", "采编", "CMS", "小程序", "直播系统", "非编", "转码", "字幕"
        ],
        "传播服务": [
            "舆情监测", "传播服务", "数据分析", "账号运营", "媒体投放", "新媒体运营"
        ],
        "文化创意": [
            "文化创意", "活动策划", "展览展示", "舞美", "公关", "品牌策划"
        ]
    }
    
    # 统计各类别匹配数
    category_scores = {}
    for category, keywords in categories.items():
        score = sum(1 for kw in matched_keywords if kw in keywords)
        if score > 0:
            category_scores[category] = score
    
    # 返回得分最高的类别
    if category_scores:
        return max(category_scores, key=category_scores.get)
    
    return "其他"


def filter_by_region(text: str) -> bool:
    """
    判断是否为目标地域（温州）
    """
    if not text:
        return False
    
    for region in config.TARGET_REGIONS:
        if region in text:
            return True
    
    return False


def extract_budget_from_text(text: str) -> float:
    """
    从文本中提取预算金额
    """
    if not text:
        return 0.0
    
    # 匹配预算金额
    patterns = [
        r'预算[金额：:\s]*(\d+[,\d]*\.?\d*)\s*万元',
        r'预算[金额：:\s]*(\d+[,\d]*)\s*元',
        r'￥\s*(\d+[,\d]*\.?\d*)\s*万元',
        r'(\d+[,\d]*\.?\d*)\s*万',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            amount = match.group(1).replace(',', '')
            if '万' in match.group(0):
                return float(amount) * 10000
            return float(amount)
    
    return 0.0


def is_high_risk(title: str, content: str = "", budget: float = None) -> List[str]:
    """
    判断是否为高风险项目
    返回风险标志列表
    """
    risk_flags = []
    text = f"{title} {content}"
    
    # 1. 截止时间临期（24小时内）
    # 需要根据实际日期判断，这里暂不实现
    
    # 2. 强本地响应要求
    local_response_patterns = [
        r'30分钟.*?到场',
        r'60分钟.*?到场',
        r'小时.*?响应',
        r'本地.*?服务'
    ]
    for pattern in local_response_patterns:
        if re.search(pattern, text):
            risk_flags.append("强本地响应")
            break
    
    # 3. 社保月份要求
    if re.search(r'\d{4}年\d{1,2}月.*?社保', text):
        risk_flags.append("社保要求")
    
    # 4. 强业绩门槛
    if re.search(r'\d+份.*?类似.*?业绩', text) or re.search(r'业绩.*?加分', text):
        risk_flags.append("强业绩门槛")
    
    # 5. 代理费计入报价
    if re.search(r'代理费.*?报价', text) or re.search(r'包含.*?代理费', text):
        risk_flags.append("代理费计入报价")
    
    # 6. 预算过低
    if budget and budget < 50000:
        risk_flags.append("预算过低")
    
    return risk_flags
