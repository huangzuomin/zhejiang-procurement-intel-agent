"""政采云抓取器 - 浙江政府采购网"""
import json
import subprocess
import logging
import urllib.parse
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import config

logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
FETCH_SCRIPT = SCRIPT_DIR / "scripts" / "fetch_zcy.js"


class ZCYFetcher:
    """政采云抓取器"""
    
    def __init__(self):
        self.base_url = "https://zfcg.czt.zj.gov.cn"
        self.categories = [
            # 采购意向
            {"name": "采购意向", "url": "https://zfcg.czt.zj.gov.cn/site/category?parentId=600007&childrenCode=ZcyAnnouncement"},
            # 招标公告
            {"name": "招标公告", "url": "https://zfcg.czt.zj.gov.cn/site/category?parentId=600007&childrenCode=ZcyAnnouncement701"},
        ]
    
    def fetch_notices(self) -> List[Dict]:
        """使用 Puppeteer 抓取公告"""
        logger.info("启动政采云 Puppeteer 抓取...")
        
        try:
            result = subprocess.run(
                ["node", str(FETCH_SCRIPT)],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=str(SCRIPT_DIR)
            )
            
            if result.returncode != 0:
                logger.error(f"Puppeteer 错误: {result.stderr}")
                return []
            
            # 解析 JSON 输出
            output = result.stdout
            json_start = output.find('JSON_START')
            json_end = output.find('JSON_END')
            
            if json_start != -1 and json_end != -1:
                json_str = output[json_start + 10:json_end].strip()
                notices = json.loads(json_str)
                logger.info(f"抓取成功: {len(notices)} 条公告")
                return notices
            else:
                logger.warning("未找到 JSON 输出")
                return []
                
        except subprocess.TimeoutExpired:
            logger.error("Puppeteer 超时")
            return []
        except Exception as e:
            logger.error(f"Puppeteer 抓取失败: {e}")
            return []
    
    def transform_to_notice(self, item: Dict) -> Dict:
        """转换为标准公告格式"""
        # 解析 URL 获取 articleId
        article_id = item.get('id', '')
        
        # 构建详情页 URL
        detail_url = item.get('href', '')
        
        # 从标题提取日期和区域
        title = item.get('title', '')
        
        # 提取区域 (如 "诸暨市", "江山市")
        region = "浙江"
        if "杭州市" in title:
            region = "杭州"
        elif "宁波市" in title:
            region = "宁波"
        elif "温州市" in title:
            region = "温州"
        elif "绍兴市" in title:
            region = "绍兴"
        elif "湖州市" in title:
            region = "湖州"
        elif "嘉兴市" in title:
            region = "嘉兴"
        elif "金华市" in title:
            region = "金华"
        elif "衢州市" in title:
            region = "衢州"
        elif "舟山市" in title:
            region = "舟山"
        elif "台州市" in title:
            region = "台州"
        elif "丽水市" in title:
            region = "丽水"
        elif "诸暨市" in title:
            region = "绍兴"
        elif "江山市" in title:
            region = "衢州"
        elif "嵊州市" in title:
            region = "绍兴"
        
        return {
            'title': title,
            'notice_url': detail_url,
            'region': region,
            'publish_date': datetime.now().strftime('%Y-%m-%d'),
            'notice_type': 'tender',
            'source': 'zcy'  # 标记来源
        }
    
    def run_fetch(self) -> int:
        """运行抓取，返回新增数量"""
        notices = self.fetch_notices()
        
        if not notices:
            logger.warning("未抓取到任何公告")
            return 0
        
        # 转换格式
        transformed = [self.transform_to_notice(n) for n in notices]
        
        # 入库
        from db import Database
        database = Database()
        new_count = 0
        
        for notice in transformed:
            # 使用 upsert 插入或更新
            result = database.upsert_notice(
                notice_url=notice['notice_url'],
                title=notice['title'],
                source_id=1,
                region=notice['region'],
                publish_date=notice['publish_date'],
                notice_type=notice['notice_type']
            )
            if result:  # 返回 True 表示新增
                new_count += 1
        
        logger.info(f"新增 {new_count} 条公告")
        return new_count


def run_fetch():
    """独立运行函数"""
    logging.basicConfig(level=logging.INFO)
    fetcher = ZCYFetcher()
    count = fetcher.run_fetch()
    print(f"抓取完成: 新增 {count} 条")


if __name__ == "__main__":
    run_fetch()
