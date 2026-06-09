"""公告详情解析器"""
import re
import logging
from typing import Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from db import db
import config
from media_filter import is_media_related, categorize_media

logger = logging.getLogger(__name__)


class Parser:
    def __init__(self):
        self.fetch_session = None
    
    def set_session(self, session):
        self.fetch_session = session
    
    def parse_notice_detail(self, html: str, url: str) -> Dict:
        """解析公告详情"""
        soup = BeautifulSoup(html, 'html.parser')
        
        result = {
            'title': '',
            'buyer': None,
            'budget_amount': None,
            'deadline_at': None,
            'proc_method': None,
            'agent': None,
            'region': None,
            'contact_name': None,
            'contact_phone': None,
            'content_text': ''
        }
        
        # 1. 提取标题
        title_tag = soup.find('h2') or soup.find('title')
        if title_tag:
            result['title'] = title_tag.get_text(strip=True)[:200]
        
        # 2. 从表格中提取字段
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).replace('：', '').replace(':', '')
                    value = cells[1].get_text(strip=True)
                    
                    if '采购' in key and '单位' in key:
                        result['buyer'] = value
                    elif '预算' in key:
                        result['budget_amount'] = self._parse_budget(value)
                    elif '截止' in key or '开标' in key:
                        result['deadline_at'] = self._parse_datetime(value)
                    elif '采购方式' in key:
                        result['proc_method'] = value
                    elif '代理' in key and '机构' in key:
                        result['agent'] = value
                    elif '行政区域' in key:
                        result['region'] = value
        
        # 3. 从页面内容中提取
        content_div = soup.find('div', class_='vF_detail_content') or soup.find('div', class_='ann-wrapper')
        if content_div:
            text = content_div.get_text(separator=' ', strip=True)
            result['content_text'] = text[:5000]
            
            # 提取联系人
            phone_match = re.search(r'(\d{3,4}[-\s]?\d{7,8}|\d{11})', text)
            if phone_match:
                result['contact_phone'] = phone_match.group(1)
        
        # 4. 如果没有解析到标题，从 meta 获取
        if not result['title']:
            og_title = soup.find('meta', property='og:title')
            if og_title:
                result['title'] = og_title.get('content', '')[:200]
        
        # 5. 提取 publish_date
        pub_time = soup.find('meta', attrs={'name': 'PubDate'})
        if pub_time:
            result['publish_date'] = pub_time.get('content', '')

        return result
    
    def _parse_budget(self, text: str) -> Optional[float]:
        """解析预算金额"""
        if not text:
            return None
        
        # 匹配金额：50万元、50万、500000、￥50.000000万元
        patterns = [
            r'([\d,]+)\s*万元',
            r'￥\s*([\d,]+)',
            r'预算.*?([\d,]+)\s*元',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                amount = match.group(1).replace(',', '')
                if '万元' in text:
                    amount = float(amount) * 10000
                return float(amount)
        
        return None
    
    def _parse_datetime(self, text: str) -> Optional[str]:
        """解析日期时间"""
        if not text:
            return None
        
        # 匹配格式：2026年03月10日 13:30、2026-03-10 13:30
        patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):?(\d{2})?',
            r'(\d{4})-(\d{1,2})-(\d{1,2})\s*(\d{1,2}):?(\d{2})?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if len(match.groups()) == 5:
                        year, month, day, hour, minute = match.groups()
                        minute = minute or '00'
                        return f"{year}-{int(month):02d}-{int(day):02d} {int(hour):02d}:{minute}"
                    elif len(match.groups()) == 3:
                        year, month, day = match.groups()
                        return f"{year}-{int(month):02d}-{int(day):02d}"
                except:
                    pass
        
        return None
    
    def run_parse(self):
        """执行解析任务"""
        logger.info("=" * 50)
        logger.info("开始解析公告...")
        
        # 获取待解析的公告
        notices = db.get_notices_by_status('new', limit=50)
        
        if not notices:
            logger.info("没有待解析的公告")
            return 0
        
        logger.info(f"待解析公告: {len(notices)} 条")
        
        parsed_count = 0
        media_count = 0
        
        for notice in notices:
            try:
                # 抓取详情页
                from fetcher import Fetcher
                fetcher = Fetcher()
                html = fetcher.fetch_notice_detail(notice['notice_url'])
                
                if not html:
                    db.update_notice_status(
                        notice['id'], 'error', 
                        error_reason='抓取失败',
                        retry_count=notice.get('retry_count', 0) + 1
                    )
                    continue
                
                # 解析详情
                fields = self.parse_notice_detail(html, notice['notice_url'])
                
                # 更新公告状态
                db.update_notice_status(notice['id'], 'parsed')
                
                # 媒体业务过滤
                title = fields.get('title', '') or notice['title']
                content = fields.get('content_text', '')
                
                is_media, matched_keywords = is_media_related(title, content)
                
                if is_media:
                    # 分类
                    category = categorize_media(matched_keywords)
                    
                    # 风险标红
                    risk_flags = self._check_risk_flags(fields)
                    
                    # 匹配得分
                    match_score = len(matched_keywords) * 10
                    
                    # 入库项目
                    db.upsert_project(
                        notice_id=notice['id'],
                        title=title,
                        buyer=fields.get('buyer'),
                        budget_amount=fields.get('budget_amount'),
                        deadline_at=fields.get('deadline_at'),
                        proc_method=fields.get('proc_method'),
                        agent=fields.get('agent'),
                        category=category,
                        tags=matched_keywords,
                        risk_flags=risk_flags,
                        match_score=match_score
                    )
                    
                    media_count += 1
                    logger.info(f"媒体业务: {title[:30]}...")
                
                parsed_count += 1
                
            except Exception as e:
                logger.error(f"解析失败: {e}")
                db.update_notice_status(
                    notice['id'], 'error',
                    error_reason=str(e)[:200],
                    retry_count=notice.get('retry_count', 0) + 1
                )
                continue
        
        logger.info(f"解析完成: {parsed_count} 条，媒体业务: {media_count} 条")
        logger.info("=" * 50)
        
        return parsed_count
    
    def _check_risk_flags(self, fields: Dict) -> list:
        """检查风险标红"""
        risk_flags = []
        
        # 1. 截止临期
        deadline = fields.get('deadline_at')
        if deadline:
            try:
                deadline_dt = datetime.strptime(deadline[:16], "%Y-%m-%d %H:%M")
                now = datetime.now()
                hours_left = (deadline_dt - now).total_seconds() / 3600
                if 0 < hours_left < 72:
                    risk_flags.append("截止临期")
            except:
                pass
        
        # 2. 预算过低
        budget = fields.get('budget_amount')
        if budget and budget < 50000:
            risk_flags.append("预算过低")
        
        return risk_flags


def main():
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = Parser()
    parser.run_parse()


if __name__ == "__main__":
    main()
