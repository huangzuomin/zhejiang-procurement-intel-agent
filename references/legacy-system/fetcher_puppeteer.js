/**
 * 政采云公告抓取器 (Puppeteer) - 优化版
 */

const puppeteer = require('puppeteer');

async function fetchNotices() {
    console.log('[Puppeteer] 启动浏览器...');
    
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    });
    
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    
    // 访问采购意向页面
    const url = 'https://zfcg.czt.zj.gov.cn/site/category?parentId=600007&childrenCode=ZcyAnnouncement';
    console.log(`[Puppeteer] 访问: ${url}`);
    
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 90000 });
    await new Promise(r => setTimeout(r, 5000)); // 等待更多时间让 JS 加载
    
    // 获取公告列表
    const notices = await page.evaluate(() => {
        const items = [];
        
        // 尝试多种选择器
        const selectors = [
            '.article-list a',
            '.notice-list a',
            '.c_list a', 
            '[class*="list"] a',
            'ul li a'
        ];
        
        for (const sel of selectors) {
            const links = document.querySelectorAll(sel);
            if (links.length > 0) {
                console.log(`Found ${links.length} links with: ${sel}`);
                
                links.forEach(el => {
                    const href = el.href;
                    let title = el.textContent?.trim() || '';
                    
                    // 尝试从 title 属性获取
                    if (!title || title.length < 5) {
                        title = el.getAttribute('title') || '';
                    }
                    
                    if (href && href.includes('detail') && href.includes('articleId') && title.length > 5) {
                        const match = href.match(/articleId=([^&]+)/);
                        const id = match ? decodeURIComponent(match[1]) : '';
                        
                        items.push({
                            url: href,
                            title: title.substring(0, 150),
                            id
                        });
                    }
                });
                break;
            }
        }
        
        // 去重
        const unique = [...new Map(items.map(n => [n.id || n.url, n])).values()];
        return unique.slice(0, 20); // 限制数量
    });
    
    console.log(`[Puppeteer] 找到 ${notices.length} 条公告`);
    
    // 获取每条公告的详情
    const results = [];
    
    for (const notice of notices) {
        try {
            console.log(`[Puppeteer] 抓取: ${notice.title.substring(0, 30)}...`);
            
            await page.goto(notice.url, { waitUntil: 'networkidle2', timeout: 60000 });
            await new Promise(r => setTimeout(r, 3000)); // 等待详情加载
            
            const detail = await page.evaluate(() => {
                const result = {
                    title: '',
                    buyer: '',
                    budget: '',
                    deadline: '',
                    region: '',
                    content: ''
                };
                
                // 从页面获取完整内容
                const bodyText = document.body.innerText;
                
                // 提取标题 - 查找 h1, h2
                const h1 = document.querySelector('h1')?.innerText || '';
                const h2 = document.querySelector('h2')?.innerText || '';
                result.title = h1 || h2 || '获取失败';
                
                // 从完整文本中提取关键字段
                const lines = bodyText.split('\n').filter(l => l.trim());
                
                for (const line of lines) {
                    if (line.includes('采购单位') || line.includes('单位名称')) {
                        result.buyer = line.replace(/.*采购单位.*?:?/, '').trim().substring(0, 50);
                    }
                    if (line.includes('预算') && line.includes('金额')) {
                        result.budget = line.replace(/.*预算.*?:?/, '').trim().substring(0, 30);
                    }
                    if (line.includes('意向') || line.includes('时间')) {
                        result.deadline = line.replace(/.*时间.*?:?/, '').trim().substring(0, 30);
                    }
                    if (line.includes('区域') || line.includes('行政区')) {
                        result.region = line.replace(/.*区域.*?:?/, '').trim().substring(0, 30);
                    }
                }
                
                // 获取内容摘要
                const contentEl = document.querySelector('[class*="content"], .detail, .article-content');
                result.content = contentEl ? contentEl.innerText.substring(0, 3000) : bodyText.substring(0, 3000);
                
                return result;
            });
            
            results.push({
                ...notice,
                ...detail,
                type: 'intention',
                fetched_at: new Date().toISOString()
            });
            
        } catch (e) {
            console.log(`[Puppeteer] 详情抓取失败: ${e.message}`);
            results.push({
                ...notice,
                type: 'intention',
                error: e.message
            });
        }
    }
    
    await browser.close();
    
    return {
        success: true,
        count: results.length,
        notices: results
    };
}

// 运行
fetchNotices()
    .then(result => {
        console.log('\n--- RESULT JSON ---');
        console.log(JSON.stringify(result, null, 2));
    })
    .catch(err => {
        console.error('Error:', err);
        process.exit(1);
    });
