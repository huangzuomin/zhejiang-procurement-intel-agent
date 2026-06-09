const puppeteer = require('puppeteer');

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
