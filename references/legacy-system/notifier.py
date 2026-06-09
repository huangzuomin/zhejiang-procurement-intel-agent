"""通知推送"""
import json
import logging
import requests
from typing import List, Dict
import config
from db import db

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or config.DISCORD_WEBHOOK_URL
    
    def send_embed(self, embeds: List[Dict]) -> bool:
        """发送嵌入消息"""
        if not self.webhook_url:
            logger.warning("未配置 Discord Webhook URL")
            return False
        
        try:
            response = requests.post(
                self.webhook_url,
                json={"embeds": embeds},
                timeout=10
            )
            
            if response.status_code == 204 or response.status_code == 200:
                logger.info("推送成功")
                return True
            else:
                logger.error(f"推送失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"推送异常: {e}")
            return False
    
    def notify_new_projects(self, projects: List[Dict]):
        """推送新增项目"""
        if not projects:
            logger.info("没有新增项目需要推送")
            return
        
        # 限制单次推送数量
        display_projects = projects[:10]
        
        embeds = []
        
        for p in display_projects:
            # 构建字段
            fields = []
            
            if p.get('buyer'):
                fields.append({
                    "name": "采购单位",
                    "value": p['buyer'][:50],
                    "inline": True
                })
            
            if p.get('budget_amount'):
                budget_str = f"¥{p['budget_amount']:,.0f}"
                fields.append({
                    "name": "预算",
                    "value": budget_str,
                    "inline": True
                })
            
            if p.get('category'):
                fields.append({
                    "name": "类别",
                    "value": p['category'],
                    "inline": True
                })
            
            if p.get('deadline_at'):
                fields.append({
                    "name": "截止时间",
                    "value": p['deadline_at'][:16],
                    "inline": True
                })
            
            # 风险标红
            risk_flags = json.loads(p.get('risk_flags', '[]'))
            if risk_flags:
                fields.append({
                    "name": "⚠️ 风险",
                    "value": ", ".join(risk_flags),
                    "inline": False
                })
            
            # 标签
            tags = json.loads(p.get('tags', '[]'))
            if tags:
                fields.append({
                    "name": "标签",
                    "value": " ".join(tags[:5]),
                    "inline": False
                })
            
            embed = {
                "title": p['title'][:100],
                "url": f"http://www.ccgp.gov.cn/detail?id={p['notice_id']}",
                "color": 58178,  # 蓝色
                "fields": fields,
                "footer": {
                    "text": f"匹配度: {p.get('match_score', 0)}分 | {p.get('category', '其他')}"
                }
            }
            
            embeds.append(embed)
        
        # 添加摘要
        if len(projects) > 10:
            summary_embed = {
                "title": f"📊 今日共 {len(projects)} 条媒体业务相关公告",
                "description": f"展示前 10 条，完整列表请查看数据库",
                "color": 3066993  # 绿色
            }
            embeds.insert(0, summary_embed)
        
        self.send_embed(embeds)
    
    def notify_stats(self, stats: Dict):
        """推送统计信息"""
        embed = {
            "title": "📈 政采情报库 - 每日统计",
            "color": 3066993,
            "fields": [
                {
                    "name": "待解析公告",
                    "value": str(stats.get('new_notices', 0)),
                    "inline": True
                },
                {
                    "name": "已解析公告",
                    "value": str(stats.get('parsed_notices', 0)),
                    "inline": True
                },
                {
                    "name": "总项目数",
                    "value": str(stats.get('total_projects', 0)),
                    "inline": True
                },
                {
                    "name": "今日新增",
                    "value": str(stats.get('today_projects', 0)),
                    "inline": True
                }
            ],
            "footer": {
                "text": "政采情报库 MVP"
            }
        }
        
        self.send_embed([embed])
    
    def run_notify(self):
        """执行推送任务"""
        logger.info("=" * 50)
        logger.info("开始推送通知...")
        
        # 获取今日新增项目
        projects = db.get_today_projects()
        
        # 推送新增项目
        self.notify_new_projects(projects)
        
        # 推送统计
        stats = db.get_stats()
        self.notify_stats(stats)
        
        logger.info("推送完成")
        logger.info("=" * 50)


def main():
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    notifier = Notifier()
    notifier.run_notify()


if __name__ == "__main__":
    main()
