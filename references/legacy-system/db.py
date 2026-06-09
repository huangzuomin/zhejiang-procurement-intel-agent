"""数据库操作"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import config

class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DATABASE_PATH
        self._init_db()
    
    def _get_conn(self):
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # sources 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                base_url TEXT NOT NULL,
                region TEXT DEFAULT '温州',
                notice_type TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # notices 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            )
        """)
        
        # projects 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notice_id INTEGER REFERENCES notices(id),
                project_key TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                buyer TEXT,
                budget_amount REAL,
                deadline_at TIMESTAMP,
                proc_method TEXT,
                agent TEXT,
                category TEXT,
                tags TEXT DEFAULT '[]',
                risk_flags TEXT DEFAULT '[]',
                match_score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # subscriptions 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                region TEXT,
                category TEXT,
                keywords TEXT,
                min_budget REAL,
                enabled INTEGER DEFAULT 1,
                webhook_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notices_status ON notices(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notices_region ON notices(region)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notices_publish_date ON notices(publish_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_category ON projects(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")
        
        conn.commit()
        conn.close()
    
    def upsert_notice(self, notice_url: str, title: str, source_id: int = None, 
                      region: str = None, publish_date: str = None, 
                      notice_type: str = None) -> int:
        """插入或更新公告"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO notices (notice_url, title, source_id, region, publish_date, notice_type)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(notice_url) DO UPDATE SET
                title = excluded.title,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (notice_url, title, source_id, region, publish_date, notice_type))
        
        notice_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return notice_id
    
    def get_notices_by_status(self, status: str = "new", limit: int = 100) -> List[Dict]:
        """根据状态获取公告"""
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM notices 
            WHERE status = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (status, limit))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def update_notice_status(self, notice_id: int, status: str, 
                            error_reason: str = None, retry_count: int = None):
        """更新公告状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        if retry_count is not None:
            cursor.execute("""
                UPDATE notices 
                SET status = ?, error_reason = ?, retry_count = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, error_reason, retry_count, notice_id))
        else:
            cursor.execute("""
                UPDATE notices 
                SET status = ?, error_reason = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, error_reason, notice_id))
        
        conn.commit()
        conn.close()
    
    def upsert_project(self, notice_id: int, title: str, 
                      buyer: str = None, budget_amount: float = None,
                      deadline_at: str = None, proc_method: str = None,
                      agent: str = None, category: str = None,
                      tags: List[str] = None, risk_flags: List[str] = None,
                      match_score: int = 0) -> int:
        """插入或更新项目"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 生成 project_key
        project_key = f"{title[:50]}_{notice_id}"
        
        tags_json = json.dumps(tags or [])
        risk_flags_json = json.dumps(risk_flags or [])
        
        cursor.execute("""
            INSERT INTO projects (
                notice_id, project_key, title, buyer, budget_amount, 
                deadline_at, proc_method, agent, category, 
                tags, risk_flags, match_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_key) DO UPDATE SET
                buyer = excluded.buyer,
                budget_amount = excluded.budget_amount,
                deadline_at = excluded.deadline_at,
                proc_method = excluded.proc_method,
                agent = excluded.agent,
                category = excluded.category,
                tags = excluded.tags,
                risk_flags = excluded.risk_flags,
                match_score = excluded.match_score,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (notice_id, project_key, title, buyer, budget_amount, 
              deadline_at, proc_method, agent, category,
              tags_json, risk_flags_json, match_score))
        
        project_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return project_id
    
    def get_projects(self, category: str = None, status: str = None, 
                    limit: int = 100) -> List[Dict]:
        """获取项目列表"""
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM projects WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_today_projects(self) -> List[Dict]:
        """获取今日新增项目"""
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM projects 
            WHERE date(created_at) = date('now')
            ORDER BY created_at DESC
        """)
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def add_source(self, name: str, base_url: str, region: str, notice_type: str) -> int:
        """添加数据源"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sources (name, base_url, region, notice_type)
            VALUES (?, ?, ?, ?)
            ON CONFLICT DO NOTHING
            RETURNING id
        """, (name, base_url, region, notice_type))
        
        result = cursor.fetchone()
        source_id = result[0] if result else None
        conn.commit()
        conn.close()
        return source_id
    
    def get_sources(self, enabled: bool = True) -> List[Dict]:
        """获取数据源列表"""
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM sources"
        if enabled:
            query += " WHERE enabled = 1"
        
        cursor.execute(query)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM notices WHERE status = 'new'")
        new_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM notices WHERE status = 'parsed'")
        parsed_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM projects")
        projects_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM projects WHERE date(created_at) = date('now')")
        today_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "new_notices": new_count,
            "parsed_notices": parsed_count,
            "total_projects": projects_count,
            "today_projects": today_count
        }


# 全局数据库实例
db = Database()
