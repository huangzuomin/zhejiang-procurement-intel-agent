"""基于 Puppeteer 的公告抓取器"""
import json
import subprocess
import logging
from typing import List, Dict
from pathlib import Path
import config

logger = logging.getLogger(__name__)

# Puppeteer 脚本路径
SCRIPT_DIR = Path(__file__).parent
FETCH_SCRIPT = SCRIPT_DIR / "scripts" / "fetch_zcy.js"


def ensure_puppeteer_script():
    """确保 Puppeteer 脚本存在"""
    FETCH_SCRIPT.parent.mkdir(exist_ok=True)
    
    if not FETCH_SCRIPT.exists():
        script = '''const puppeteer = require('puppeteer');

async function fetchNotices() {
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    
    const allNotices = [];
    
    // 访问采购意向页面
    console.log('抓取采购意向...');
    await page.goto('https://zfcg.czt.zj.gov.cn/site/category?parentId=600007&childrenCode=ZcyAnnouncement', { 
        waitUntil: 'networkidle2', 
        timeout: 60000 
    });
    await new Promise(r => setTimeout(r, 3000));
    
    const notices = await page.evaluate(() => {
        const items = [];
        const elements = document.querySelectorAll('.article-list a, .notice-list a, .c_list a, ul li a');
        elements.forEach(el => {
            const href = el.href;
            const title = el.textContent?.trim() || el.getAttribute('title');
            if (href && href.includes('detail') && title && title.length > 5) {
                const idMatch = href.match(/articleId=([^&]+)/);
                items.push({ 
                    href, 
                    title: title.substring(0, 150),
                    id: idMatch ? idMatch[1] : ''
                });
            }
        });
        return items;
    });
    
    console.error(`Found ${notices.length} notices`);
    allNotices.push(...notices);
    
    await browser.close();
    
    // 输出 JSON
    console.log('JSON_START');
    console.log(JSON.stringify(allNotices, null, 2));
    console.log('JSON_END');
}

fetchNotices().catch(e => { console.error(e); process.exit(1); });
'''
        FETCH_SCRIPT.write_text(script, encoding='utf-8')
        logger.info(f"创建 Puppeteer 脚本: {FETCH_SCRIPT}")


def fetch_with_puppeteer() -> List[Dict]:
    """使用 Puppeteer 抓取公告"""
    ensure_puppeteer_script()
    
    logger.info("启动 Puppeteer 抓取...")
    
    try:
        # 运行 Node.js 脚本
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


def fetch_notice_detail(url: str) -> str:
    """抓取公告详情页（静态 HTML 方式）"""
    import requests
    
    try:
        response = requests.get(url, timeout=60, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        if response.status_code == 200:
            return response.text
    except Exception as e:
        logger.error(f"详情页抓取失败: {e}")
    
    return ""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    notices = fetch_with_puppeteer()
    print(f"抓取到 {len(notices)} 条公告")
    
    for n in notices[:5]:
        print(f"- {n['title'][:40]}")
