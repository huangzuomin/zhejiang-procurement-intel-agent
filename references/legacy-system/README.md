# 政采情报库

## 环境要求
- Python 3.9+
- SQLite

## 安装依赖
```bash
pip install -r requirements.txt
```

## 初始化数据库
```bash
python init_db.py
```

## 运行
```bash
python main.py
```

## 定时任务
```bash
# 添加到 crontab
0 6 * * * /usr/bin/python3 /path/to/main.py >> /var/log/govproc.log 2>&1
```
