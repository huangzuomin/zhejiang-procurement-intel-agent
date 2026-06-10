#!/usr/bin/env node
"use strict";

/**
 * Full daily collection + detail enrichment + brief generation for DingTalk.
 * Usage: node scripts/full_collect_and_brief.js [--mode am|pm|full] [--today YYYY-MM-DD]
 *
 * Flow:
 *   1. Read intention list + bid list from data/latest_intentions.json / data/latest_bids.json
 *      (populated by browser tool extraction)
 *   2. Enrich each notice via portal detail API
 *   3. Classify + score
 *   4. Generate DingTalk-ready brief
 *   5. Diff against AM snapshot if mode=pm
 */

const fs = require("fs");
const path = require("path");
const https = require("https");

const ROOT = path.resolve(__dirname, "..");
const DATA_DIR = path.join(ROOT, "data");
const REPORTS_DIR = path.join(ROOT, "reports", "latest_daily_pipeline");

const TODAY = process.argv.find((a, i) => process.argv[i - 1] === "--today") || new Date().toISOString().slice(0, 10);
const MODE = process.argv.find((a, i) => process.argv[i - 1] === "--mode") || "full";

// Media relevance keywords
const MEDIA_KEYWORDS = [
  "融媒体", "新媒体", "网站建设", "网站运维", "视频拍摄", "视频制作", "宣传片",
  "短视频", "直播", "微信公众号", "视频号", "新闻策划", "新闻采编", "内容运营",
  "媒体传播", "宣传服务", "文化传播", "政务新媒体", "数字化传播", "舆情",
  "GEO", "搜索引擎优化", "SEO", "内容制作", "图文设计", "视觉设计",
  "活动策划", "品牌宣传", "信息化建设", "信息系统建设", "智慧城市",
  "政务公开", "政府信息公开", "门户网站", "APP开发", "小程序",
];

const MEDIA_EXCLUDE = [
  "物业管理", "劳务派遣", "保洁", "保安", "餐饮", "食堂", "食堂承包",
  "绿化", "园林绿化", "医疗设备", "医疗器械", "药品", "教学一体机",
  "办公家具", "办公用品", "校服", "学生奶", "保险",
];

function fetchJSON(url, timeoutMs = 15000) {
  return new Promise((resolve, reject) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const urlObj = new URL(url);
    const options = {
      hostname: urlObj.hostname,
      path: urlObj.pathname + urlObj.search,
      method: "GET",
      headers: {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
        Accept: "application/json,text/plain,*/*",
        Referer: "https://zfcg.czt.zj.gov.cn/",
      },
      signal: controller.signal,
    };
    const req = https.request(options, (res) => {
      let body = "";
      res.on("data", (chunk) => (body += chunk));
      res.on("end", () => {
        clearTimeout(timer);
        try {
          resolve(JSON.parse(body));
        } catch {
          resolve(null);
        }
      });
    });
    req.on("error", (err) => {
      clearTimeout(timer);
      resolve(null);
    });
    req.on("aborted", () => {
      clearTimeout(timer);
      resolve(null);
    });
    req.end();
  });
}

async function enrichNotice(articleId) {
  const ts = Math.floor(Date.now() / 1000);
  const url = `https://zfcg.czt.zj.gov.cn/portal/detail?articleId=${encodeURIComponent(articleId)}&timestamp=${ts}`;
  const payload = await fetchJSON(url);
  if (!payload?.success || !payload.result?.data) return null;

  const data = payload.result.data;
  const html = data.content || "";
  const text = html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;|&#160;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 3000);

  const budgetMatch = text.match(/(?:预算金额|预算|最高限价)[^。；;]{0,20}?([\d,.]+)\s*万元/);
  const budgetYuanMatch = !budgetMatch && text.match(/(?:预算金额|预算|最高限价)[^。；;]{0,20}?([\d,.]+)\s*元/);
  const buyerMatch =
    text.match(/采购人信息\s*名\s*称[:：]?\s*(.+?)(?=\s+地\s*址|\s+传\s*真|\s+项目联系人|\s+联系方式|\s+采购代理|$)/) ||
    text.match(/采购人[:：]\s*(.+?)(?=\s+采购项目|$)/);
  const deadlineMatch = text.match(
    /(?:提交投标文件截止时间|截止时间|开标时间)[^。；;]{0,30}?(\d{4}[年-]\d{1,2}[月-]\d{1,2})/
  );

  let budget = null;
  if (budgetMatch) {
    budget = parseFloat(budgetMatch[1].replace(/,/g, "")) * 10000;
  } else if (budgetYuanMatch) {
    budget = parseFloat(budgetYuanMatch[1].replace(/,/g, ""));
  }

  return {
    title: data.title || null,
    project: data.projectName || null,
    category: (data.categoryNames || []).join(" > "),
    buyer: buyerMatch ? buyerMatch[1].trim() : (data.author || null),
    budget,
    budgetDisplay: budget ? (budget >= 10000 ? (budget / 10000).toFixed(budget % 10000 === 0 ? 0 : 1) + "万元" : budget + "元") : null,
    deadline: deadlineMatch ? normalizeDate(deadlineMatch[1]) : null,
    publishDate: data.publishDate ? new Date(data.publishDate).toISOString().slice(0, 10) : null,
    contact: text.match(/联系人[:：]\s*(.+?)(?=\s+联系电话|\s+联系)/)?.[1]?.trim() || null,
    phone: text.match(/联系电话[:：]\s*([\d-]+)/)?.[1]?.trim() || null,
    textSnippet: text.slice(0, 600),
  };
}

function normalizeDate(value) {
  if (!value) return null;
  const nums = String(value).match(/\d+/g);
  if (!nums || nums.length < 3) return String(value).trim() || null;
  return `${nums[0].padStart(4, "0")}-${nums[1].padStart(2, "0")}-${nums[2].padStart(2, "0")}`;
}

function extractArticleId(url) {
  try {
    return new URL(url).searchParams.get("articleId");
  } catch {
    return null;
  }
}

function classifyNotice(notice) {
  const combined = `${notice.title} ${notice.detail?.project || ""} ${notice.detail?.textSnippet || ""} ${notice.category}`;
  const hasMedia = MEDIA_KEYWORDS.some((kw) => combined.includes(kw));
  const hasExclude = MEDIA_EXCLUDE.some((kw) => combined.includes(kw));
  const isBid = notice.noticeType === "招标公告";

  if (hasMedia && !hasExclude) {
    if (isBid) return { cls: "A", label: "A类·强烈建议关注", reasons: MEDIA_KEYWORDS.filter((kw) => combined.includes(kw)) };
    return { cls: "B", label: "B类·值得关注", reasons: MEDIA_KEYWORDS.filter((kw) => combined.includes(kw)) };
  }
  if (hasExclude) return { cls: "D", label: "D类·排除", reasons: [] };
  if (notice.region === "温州市" || notice.region === "鹿城区" || notice.region === "龙湾区" || notice.region === "瓯海区" || notice.region === "乐清市" || notice.region === "瑞安市") {
    return { cls: "C", label: "C类·温州地区可关注", reasons: ["温州地区"] };
  }
  return { cls: "D", label: "D类·排除", reasons: [] };
}

function loadJSON(filepath) {
  try {
    return JSON.parse(fs.readFileSync(filepath, "utf8"));
  } catch {
    return null;
  }
}

function formatBudget(value) {
  if (!value) return "未披露";
  if (value >= 10000) {
    return `${(value / 10000).toFixed(value % 10000 === 0 ? 0 : 1)}万元`;
  }
  return `${value}元`;
}

function compactReasons(reasons) {
  if (!Array.isArray(reasons) || reasons.length === 0) return "需人工复核";
  return reasons.slice(0, 6).join("、");
}

function renderFocusItem(notice, index) {
  const lines = [
    `${index}. [${notice.opportunity_class}类] ${notice.title}`,
    `   ${notice.buyer || "采购人未披露"} / ${formatBudget(notice.budget)}${notice.deadline ? ` / 截止 ${notice.deadline}` : ""}`,
    `   匹配：${compactReasons(notice.classification_reasons)}`,
  ];
  if (notice.project_name && notice.project_name !== notice.title) {
    lines.push(`   项目：${notice.project_name}`);
  }
  return lines;
}

function generateBrief({
  scrapePayload,
  intentionsCount,
  bidsCount,
  enrichedCount,
  mode,
  today,
  newCount = 0,
  newNotices = [],
}) {
  const notices = scrapePayload.notices || [];
  const aItems = notices.filter((n) => n.opportunity_class === "A");
  const bItems = notices.filter((n) => n.opportunity_class === "B");
  const cItems = notices.filter((n) => n.opportunity_class === "C");
  const dItems = notices.filter((n) => n.opportunity_class === "D");
  const focusItems = [...aItems, ...bItems];
  const focusDeadlines = focusItems.filter((n) => n.deadline).slice(0, 10);

  const title = `📋 浙江政采情报${mode === "pm" ? (newCount > 0 ? "增量" : "无新增") : mode === "am" ? "日报" : "日报"} | ${today}`;
  const lines = [
    title,
    "",
    `概览：共${notices.length}条，详情${enrichedCount}条，A ${aItems.length} / B ${bItems.length} / C ${cItems.length} / D ${dItems.length}，A/B ${focusItems.length}条`,
    `来源：采购意向 ${intentionsCount} + 招标公告 ${bidsCount}`,
    "",
  ];

  if (mode === "pm") {
    lines.push(newCount > 0 ? `较上午新增 ${newCount} 条公告。` : "下午无新增公告，今日数据不变。");
    lines.push("");
    if (newCount === 0) {
      lines.push("上午已推送的重点机会不重复展开。");
      return lines.join("\n");
    }
  }

  if (focusItems.length === 0) {
    lines.push("今日无媒体/数字化重点机会。");
    lines.push("低优先级项目已归档，不在群内展开。");
    return lines.join("\n");
  }

  if (aItems.length > 0) {
    lines.push("### A类 · 立即响应");
    aItems.forEach((notice, index) => lines.push(...renderFocusItem(notice, index + 1)));
    lines.push("");
  }

  if (bItems.length > 0) {
    lines.push("### B类 · 提前跟进");
    bItems.forEach((notice, index) => lines.push(...renderFocusItem(notice, index + 1)));
    lines.push("");
  }

  if (mode === "pm" && newCount > 0 && newNotices.length > 0) {
    const newFocus = newNotices.filter((n) => n.opportunity_class === "A" || n.opportunity_class === "B");
    if (newFocus.length > 0) {
      lines.push("### 下午新增重点");
      newFocus.slice(0, 5).forEach((notice) => {
        lines.push(`- [${notice.opportunity_class}类] ${notice.title} / ${notice.buyer || "采购人未披露"} / ${formatBudget(notice.budget)}`);
      });
      if (newFocus.length > 5) lines.push(`- 另有 ${newFocus.length - 5} 条新增重点已压缩。`);
      lines.push("");
    }
  }

  if (focusDeadlines.length > 0) {
    lines.push("### 近期截止");
    focusDeadlines.forEach((notice) => {
      lines.push(`- ${notice.deadline} · [${notice.opportunity_class}类] ${notice.title}${notice.budget ? ` (${formatBudget(notice.budget)})` : ""}`);
    });
    const hiddenDeadlineCount = focusItems.filter((n) => n.deadline).length - focusDeadlines.length;
    if (hiddenDeadlineCount > 0) lines.push(`- 另有 ${hiddenDeadlineCount} 条 A/B 截止项目已压缩。`);
  }

  return lines.join("\n");
}

async function main() {
  console.log(`[collect] Mode=${MODE} Today=${TODAY}`);

  const intentionRaw = loadJSON(path.join(DATA_DIR, "latest_intentions.json")) || [];
  const bidRaw = loadJSON(path.join(DATA_DIR, "latest_bids.json")) || [];
  const intentions = Array.isArray(intentionRaw) ? intentionRaw : (intentionRaw.items || []);
  const bids = Array.isArray(bidRaw) ? bidRaw : (bidRaw.items || []);

  const allNotices = [
    ...intentions.map((n) => ({ ...n, noticeType: "采购意向公开" })),
    ...bids.map((n) => ({ ...n, noticeType: "招标公告" })),
  ];

  // Dedupe by URL
  const seen = new Set();
  const deduped = allNotices.filter((n) => {
    if (seen.has(n.url)) return false;
    seen.add(n.url);
    return true;
  });

  console.log(`[collect] Total raw: ${allNotices.length}, deduped: ${deduped.length}`);

  // Enrich via detail API in batches
  const enriched = [];
  const BATCH = 15;
  for (let i = 0; i < deduped.length; i += BATCH) {
    const batch = deduped.slice(i, i + BATCH);
    console.log(`[enrich] Batch ${Math.floor(i / BATCH) + 1}/${Math.ceil(deduped.length / BATCH)} (${i + 1}-${Math.min(i + BATCH, deduped.length)})`);
    const results = await Promise.all(
      batch.map(async (notice) => {
        const articleId = extractArticleId(notice.url);
        if (!articleId) return { ...notice, detail: null };
        const detail = await enrichNotice(articleId);
        return { ...notice, detail };
      })
    );
    enriched.push(...results);
    if (i + BATCH < deduped.length) {
      await new Promise((r) => setTimeout(r, 500));
    }
  }

  // Classify
  const classified = enriched.map((n) => ({
    ...n,
    classification: classifyNotice(n),
  }));

  // Save full data
  fs.mkdirSync(REPORTS_DIR, { recursive: true });
  fs.mkdirSync(DATA_DIR, { recursive: true });

  const scrapePayload = {
    source: "browser_full_collect",
    scraped_at: new Date().toISOString(),
    today: TODAY,
    mode: MODE,
    total_raw: allNotices.length,
    total_deduped: deduped.length,
    total_enriched: enriched.filter((n) => n.detail).length,
    notices: classified.map((n) => ({
      title: n.title,
      detail_url: n.url,
      notice_type: n.noticeType,
      source_column: n.noticeType === "采购意向公开" ? "intention" : "bid",
      publish_date: n.date || n.detail?.publishDate,
      region: n.region,
      category_code: n.category,
      buyer: n.detail?.buyer || null,
      budget: n.detail?.budget || null,
      deadline: n.detail?.deadline || null,
      project_name: n.detail?.project || null,
      contact: n.detail?.contact || null,
      phone: n.detail?.phone || null,
      text_snippet: n.detail?.textSnippet || null,
      opportunity_class: n.classification.cls,
      classification_reasons: n.classification.reasons,
    })),
  };

  fs.writeFileSync(path.join(DATA_DIR, "latest_scrape.json"), JSON.stringify(scrapePayload, null, 2));
  console.log(`[save] data/latest_scrape.json (${scrapePayload.notices.length} notices)`);

  // AM snapshot
  if (MODE === "am" || MODE === "full") {
    fs.writeFileSync(path.join(DATA_DIR, "latest_scrape_am.json"), JSON.stringify(scrapePayload, null, 2));
    console.log(`[save] data/latest_scrape_am.json (AM snapshot)`);
  }

  // PM diff
  let newCount = 0;
  let newNotices = [];
  if (MODE === "pm") {
    const amData = loadJSON(path.join(DATA_DIR, "latest_scrape_am.json"));
    if (amData) {
      const amUrls = new Set((amData.notices || []).map((n) => n.detail_url));
      newNotices = scrapePayload.notices.filter((n) => !amUrls.has(n.detail_url));
      newCount = newNotices.length;
      console.log(`[diff] PM new: ${newCount}, unchanged: ${scrapePayload.notices.length - newCount}`);
    } else {
      console.log(`[diff] AM snapshot not found, treating as full`);
    }
  }

  const aItems = scrapePayload.notices.filter((n) => n.opportunity_class === "A");
  const bItems = scrapePayload.notices.filter((n) => n.opportunity_class === "B");
  const cItems = scrapePayload.notices.filter((n) => n.opportunity_class === "C");
  const dItems = scrapePayload.notices.filter((n) => n.opportunity_class === "D");
  const brief = generateBrief({
    scrapePayload,
    intentionsCount: intentions.length,
    bidsCount: bids.length,
    enrichedCount: enriched.filter((n) => n.detail).length,
    mode: MODE,
    today: TODAY,
    newCount,
    newNotices,
  });
  fs.writeFileSync(path.join(REPORTS_DIR, "daily_brief.md"), brief);
  console.log(`\n${brief}`);
  console.log(`\n[brief] Saved to reports/latest_daily_pipeline/daily_brief.md`);

  // Summary JSON for pipeline compat
  fs.writeFileSync(
    path.join(REPORTS_DIR, "summary.json"),
    JSON.stringify(
      {
        today: TODAY,
        mode: MODE,
        total: scrapePayload.notices.length,
        enriched: enriched.filter((n) => n.detail).length,
        a: aItems.length,
        b: bItems.length,
        c: cItems.length,
        d: dItems.length,
        pm_new: MODE === "pm" ? newCount : null,
      },
      null,
      2
    )
  );
}

if (require.main === module) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = {
  generateBrief,
  formatBudget,
};
