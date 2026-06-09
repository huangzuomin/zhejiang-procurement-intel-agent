"""公告抓取器"""
import requests
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from datetime import datetime
import config
from db import db

logger = logging.getLogger(__name__)


class Fetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "http://www.ccgp.gov.cn/",
            "Connection": "keep-alive",
        })
        self.request_count = 0
    
    def _wait_if_needed(self):
        """请求间隔，防止被限流"""
        self.request_count += 1
        if self.request_count % 5 == 0:
            import time
            time.sleep(1)  # 每5次请求间隔1秒
    
    def fetch_notice_list(self, source_id: int, url: str) -> List[Dict]:
        """抓取公告列表页"""
        logger.info(f"抓取公告列表: {url}")
        
        self._wait_if_needed()
        
        try:
            response = self.session.get(url, timeout=config.FETCH_TIMEOUT)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                logger.error(f"请求失败: {response.status_code}")
                return []
            
            return self._parse_notice_list(response.text, source_id, url)
            
        except Exception as e:
            logger.error(f"抓取失败: {e}")
            return []
    
    def _parse_notice_list(self, html: str, source_id: int, url: str = "") -> List[Dict]:
        """解析公告列表页"""
        soup = BeautifulSoup(html, 'html.parser')
        notices = []
        
        # 查找公告列表 - 尝试多种选择器
        items = soup.select('li a[href*=".htm"]') or soup.select('.c_list a') or soup.select('ul li a')
        
        for item in items[:50]:  # 限制数量
            try:
                title = item.get('title', '') or item.get_text(strip=True)
                href = item.get('href', '')
                
                if not title or not href:
                    continue
                
                # 构建完整 URL
                if href.startswith('./'):
                    href = href[2:]  # 去掉 ./
                if not href.startswith('http'):
                    # 正确拼接：基于列表页 URL 的目录
                    # url = http://www.ccgp.gov.cn/cggg/dfgg/gkzb/
                    # 去掉末尾的 / 然后取目录
                    base_url = url.rstrip('/')  # 去掉末尾 /
                    href = f"{base_url}/{href}"
                
                # 过滤非公告链接 (htm/html 且非首页)
                if not (href.endswith('.htm') or href.endswith('.html')):
                    continue
                
                # 解析日期（从 URL 或标题）
                publish_date = None
                if '/t' in href:
                    try:
                        date_str = href.split('/t')[1][:8]
                        publish_date = f"20{date_str[:2]}-{date_str[2:4]}-{date_str[4:6]}"
                    except:
                        pass
                
                # 尝试从列表页提取地域
                region = '未知'
                try:
                    # 查找地域信息 (在 item 的兄弟节点中)
                    region_elem = item.find_next('em', string=lambda t: t and '地域' in t)
                    if region_elem:
                        next_em = region_elem.find_next('em')
                        if next_em:
                            region = next_em.get_text(strip=True)
                except:
                    pass
                
                notice = {
                    'title': title[:200],
                    'notice_url': href,
                    'source_id': source_id,
                    'publish_date': publish_date,
                    'region': region,
                    'notice_type': 'tender'
                }
                
                notices.append(notice)
                
            except Exception as e:
                logger.warning(f"解析列表项失败: {e}")
                continue
        
        logger.info(f"解析到 {len(notices)} 条公告")
        return notices
    
    def fetch_notice_detail(self, url: str) -> Optional[str]:
        """抓取公告详情页"""
        self._wait_if_needed()
        
        try:
            response = self.session.get(url, timeout=config.FETCH_TIMEOUT)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"详情页请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"详情页抓取失败: {e}")
            return None
    
    def run_fetch(self):
        """执行抓取任务"""
        logger.info("=" * 50)
        logger.info("开始抓取公告...")
        
        sources = db.get_sources()
        if not sources:
            # 使用默认配置
            for source in config.SOURCES:
                db.add_source(
                    name=source['name'],
                    base_url=source['base_url'],
                    region=source['region'],
                    notice_type=source['notice_type']
                )
            sources = db.get_sources()
        
        total_new = 0
        
        for source in sources:
            logger.info(f"处理数据源: {source['name']}")
            
            # 抓取列表
            notices = self.fetch_notice_list(source['id'], source['base_url'])
            
            # 入库
            for notice in notices:
                try:
                    notice_id = db.upsert_notice(
                        notice_url=notice['notice_url'],
                        title=notice['title'],
                        source_id=source['id'],
                        region=notice.get('region'),
                        publish_date=notice.get('publish_date'),
                        notice_type=source['notice_type']
                    )
                    if notice_id:
                        total_new += 1
                except Exception as e:
                    logger.warning(f"入库失败: {e}")
        
        logger.info(f"抓取完成，新增 {total_new} 条公告")
        logger.info("=" * 50)
        
        return total_new


def main():
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    fetcher = Fetcher()
    fetcher.run_fetch()


if __name__ == "__main__":
    main()
