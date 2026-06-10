#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

function loadPuppeteer() {
  try {
    return require("puppeteer");
  } catch (error) {
    const runtimePath = "/home/ai/.openclaw/workspace/scripts/zfcg-scraper/node_modules/puppeteer";
    return require(runtimePath);
  }
}

const DEFAULT_SOURCE_URL =
  "https://zfcg.czt.zj.gov.cn/site/category?parentId=600007&childrenCode=ZcyAnnouncement";

const TARGET_COLUMNS = [
  {
    key: "intention",
    path: "政府采购公告 > 采购意向 > 采购意向公开",
    path_labels: ["采购意向", "采购意向公开"],
    category_code: "110-600268",
    notice_type: "采购意向公开",
  },
  {
    key: "bid",
    path: "政府采购公告 > 采购项目公告 > 招标公告",
    path_labels: ["采购项目公告", "招标公告"],
    category_code: "110-684034",
    notice_type: "招标公告",
  },
];

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.printTargets) {
    console.log(JSON.stringify(TARGET_COLUMNS, null, 2));
    return;
  }

  const puppeteer = loadPuppeteer();
  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const page = await browser.newPage();
  page.setDefaultTimeout(args.timeoutMs);
  await page.setUserAgent(
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125 Safari/537.36"
  );

  try {
    const knownUrls = loadKnownUrls(args.knownUrlsFile);
    const notices = [];
    for (const target of args.targets) {
      await page.goto(args.sourceUrl, { waitUntil: "networkidle2", timeout: args.timeoutMs });
      await delay(args.renderWaitMs);
      await page.waitForSelector("div.search-list ul.list li a[href*='/site/detail']", {
        timeout: args.timeoutMs,
      });
      await selectTargetColumn(page, target, args.timeoutMs);

      const listItems = await collectListItems(page, args.limit, target);
      for (let index = 0; index < listItems.length; index += 1) {
        const item = normalizeListItem(listItems[index], target);
        if (!item.title || !item.detail_url) {
          continue;
        }

        let detail = {};
        if (shouldFetchDetail(item, args, knownUrls, index)) {
          detail = await fetchPortalDetail(item.detail_url, args.timeoutMs);
          if (args.delayMs > 0 && index < listItems.length - 1) {
            await delay(args.delayMs);
          }
        } else if (knownUrls.has(item.detail_url)) {
          detail = { known_url: true, detail_skipped_reason: "known_url" };
        }
        notices.push({ ...item, ...detail });
        console.error(`[${target.key} ${index + 1}/${listItems.length}] ${item.title}`);
      }
    }

    const payload = {
      source: "zfcg_browser_scraper",
      source_url: args.sourceUrl,
      scraped_at: new Date().toISOString(),
      limit: args.limit,
      detail_limit: args.details ? args.detailLimit : 0,
      columns: args.targets.map((target) => ({
        key: target.key,
        path: target.path,
        category_code: target.category_code,
      })),
      notices,
    };
    writeJson(args.output, payload);
    console.log(args.output);
  } finally {
    await browser.close();
  }
}

async function selectTargetColumn(page, target, timeoutMs) {
  const responsePromise = page
    .waitForResponse(
      (response) =>
        response.url() === "https://zfcg.czt.zj.gov.cn/portal/category" &&
        response.request().postData()?.includes(`"categoryCode":"${target.category_code}"`),
      { timeout: Math.min(timeoutMs, 15000) }
    )
    .catch(() => null);

  for (let index = 0; index < target.path_labels.length; index += 1) {
    const isLast = index === target.path_labels.length - 1;
    const result = await clickTreeLabel(page, target.path_labels[index], { expand: !isLast });
    if (!result.ok) {
      throw new Error(`Target column node not found: ${result.missing}`);
    }
    if (!isLast && result.expanded) {
      await delay(1200);
    }
  }
  await responsePromise;
  await delay(1500);
}

async function clickTreeLabel(page, label, { expand }) {
  return page.evaluate(
    ({ label: targetLabel, expand: shouldExpand }) => {
      function clean(value) {
        return String(value || "").replace(/\s+/g, "").replace(/›/g, "");
      }
      const node = [...document.querySelectorAll(".po-tree-node")].find((candidate) => {
        const nodeLabel = candidate.querySelector(".po-tree-node__label");
        return clean(nodeLabel?.innerText || nodeLabel?.textContent) === targetLabel;
      });
      if (!node) {
        return { ok: false, missing: targetLabel };
      }
      node.scrollIntoView({ block: "center" });
      if (shouldExpand) {
        const isExpanded = node.className.includes("is-expanded");
        if (!isExpanded) {
          node.querySelector(".po-tree-node__expand-icon")?.click();
          return { ok: true, expanded: true };
        }
        return { ok: true, expanded: false };
      }
      node.querySelector(".po-tree-node__content")?.click();
      return { ok: true, expanded: false };
    },
    { label, expand }
  );
}

async function collectListItems(page, limit, target) {
  const items = [];
  const seenUrls = new Set();
  while (items.length < limit) {
    const pageItems = await collectCurrentPageItems(page, limit - items.length);
    for (const item of pageItems) {
      if (!item.detail_url || seenUrls.has(item.detail_url)) {
        continue;
      }
      seenUrls.add(item.detail_url);
      items.push(item);
      if (items.length >= limit) {
        break;
      }
    }
    if (items.length >= limit) {
      break;
    }
    const advanced = await clickNextPage(page, target);
    if (!advanced) {
      break;
    }
  }
  return items;
}

async function collectCurrentPageItems(page, limit) {
  return page.$$eval(
    "div.search-list ul.list li",
    (nodes, itemLimit) =>
      nodes.slice(0, itemLimit).map((li) => {
        const link = li.querySelector("a[href*='/site/detail']");
        const regionCategoryNode = li.querySelector(".title-head");
        const publishTimeNode = li.querySelector(".publish-time");
        const regionCategory =
          regionCategoryNode?.getAttribute("title") ||
          regionCategoryNode?.innerText ||
          "";
        return {
          title: (link?.getAttribute("title") || link?.innerText || "").trim(),
          detail_url: link ? new URL(link.getAttribute("href"), location.href).href : "",
          publish_date: (publishTimeNode?.innerText || "").trim(),
          region_category: regionCategory.replace(/\s+/g, ""),
          list_text: li.innerText.replace(/\s+/g, " ").trim(),
        };
      }),
    limit
  );
}

async function clickNextPage(page, target) {
  const responsePromise = page
    .waitForResponse(
      (response) =>
        response.url() === "https://zfcg.czt.zj.gov.cn/portal/category" &&
        response.request().postData()?.includes(`"categoryCode":"${target.category_code}"`),
      { timeout: 15000 }
    )
    .catch(() => null);
  const clicked = await page.evaluate(() => {
    const nextButton = document.querySelector(".po-pagination .btn-next, .btn-next");
    if (!nextButton || nextButton.disabled || nextButton.className.includes("disabled")) {
      return false;
    }
    nextButton.click();
    return true;
  });
  if (!clicked) {
    return false;
  }
  await responsePromise;
  await delay(1500);
  return true;
}

function normalizeListItem(item, target) {
  const [region, categoryCode] = splitRegionCategory(item.region_category);
  return {
    title: item.title,
    detail_url: item.detail_url,
    source_column: target.key,
    source_column_path: target.path,
    source_category_code: target.category_code,
    notice_type: target.notice_type,
    publish_date: normalizeDate(item.publish_date),
    region,
    category_code: categoryCode,
    buyer: null,
    budget: null,
    deadline: null,
    raw_detail_text: null,
  };
}

async function fetchPortalDetail(detailUrl, timeoutMs) {
  const articleId = extractArticleId(detailUrl);
  if (!articleId) {
    return { detail_error: "missing articleId" };
  }
  const apiUrl = `https://zfcg.czt.zj.gov.cn/portal/detail?articleId=${encodeURIComponent(
    articleId
  )}&timestamp=${Math.floor(Date.now() / 1000)}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(apiUrl, {
      signal: controller.signal,
      headers: {
        "user-agent":
          "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
        accept: "application/json,text/plain,*/*",
        referer: detailUrl,
      },
    });
    if (!response.ok) {
      return { detail_error: `portal detail HTTP ${response.status}` };
    }
    const payload = await response.json();
    const data = payload?.result?.data;
    if (!payload?.success || !data) {
      return { detail_error: "portal detail returned no data" };
    }
    const rawDetailText = htmlToText(data.content || "");
    const budget = parseBudget(rawDetailText);
    return {
      title: data.title || undefined,
      notice_type: Array.isArray(data.categoryNames)
        ? data.categoryNames[data.categoryNames.length - 1] || undefined
        : undefined,
      publish_date: data.publishDate ? new Date(data.publishDate).toISOString().slice(0, 10) : undefined,
      buyer: extractBuyer(rawDetailText) || data.author || null,
      budget,
      deadline: extractDeadline(rawDetailText),
      raw_detail_text: rawDetailText || null,
      portal_detail_url: apiUrl,
      project_name: data.projectName || null,
    };
  } catch (error) {
    return { detail_error: error.message };
  } finally {
    clearTimeout(timeout);
  }
}

function extractArticleId(detailUrl) {
  try {
    return new URL(detailUrl).searchParams.get("articleId");
  } catch (_error) {
    return null;
  }
}

function splitRegionCategory(value) {
  const clean = (value || "").replace(/\s+/g, "");
  if (!clean) {
    return [null, null];
  }
  const parts = clean.split("·");
  return [parts[0] || null, parts.slice(1).join("·") || null];
}

function htmlToText(html) {
  return String(html || "")
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
    .slice(0, 12000);
}

function extractBuyer(text) {
  const patterns = [
    /采购人信息\s*名\s*称[:：]?\s*(.+?)(?=\s+地\s*址[:：]|\s+传\s*真[:：]|\s+项目联系人|\s+联系方式[:：]|\s+采购代理机构|\s+项目联系方式|$)/,
    /采购人[:：]\s*(.+?)(?=\s+采购项目名称|\s+预算金额|\s+采购需求|\s+联系人|$)/,
    /采购单位\s*[:：]?\s*(.+?)(?=\s+采购项目名称|\s+预算金额|\s+采购需求|\s+联系人|$)/,
  ];
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) {
      return match[1].trim();
    }
  }
  return null;
}

function parseBudget(text) {
  const patterns = [
    /(?:预算金额|预算|最高限价)[^。；;]{0,20}?([\d,.]+)\s*万元/,
    /(?:预算金额|预算|最高限价)[^。；;]{0,20}?([\d,.]+)\s*元/,
    /(?:预算金额|预算|最高限价)\s*[（(]\s*元\s*[）)]\s*[:：]?\s*([\d,.]+)/,
  ];
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (!match) {
      continue;
    }
    let amount = Number(match[1].replace(/,/g, ""));
    if (!Number.isFinite(amount)) {
      return null;
    }
    if (match[0].includes("万元")) {
      amount *= 10000;
    }
    return amount;
  }
  return null;
}

function extractDeadline(text) {
  const match = text.match(
    /(?:提交投标文件截止时间|响应文件提交截止时间|开标时间|截止时间)[^。；;]{0,30}?(\d{4}[年-]\d{1,2}[月-]\d{1,2})/
  );
  return match ? normalizeDate(match[1]) : null;
}

function normalizeDate(value) {
  if (!value) {
    return null;
  }
  const numbers = String(value).match(/\d+/g);
  if (!numbers || numbers.length < 3) {
    return String(value).trim() || null;
  }
  return `${numbers[0].padStart(4, "0")}-${numbers[1].padStart(2, "0")}-${numbers[2].padStart(2, "0")}`;
}

function parseArgs(argv) {
  const args = {
    sourceUrl: DEFAULT_SOURCE_URL,
    limit: 15,
    detailLimit: 15,
    output: "reports/latest_scrape_quality/zfcg-browser-scrape.json",
    timeoutMs: 45000,
    renderWaitMs: 5000,
    delayMs: 800,
    details: true,
    knownUrlsFile: null,
    printTargets: false,
    targetKeys: [],
  };
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    const value = argv[index + 1];
    if (key === "--print-targets") {
      args.printTargets = true;
    } else if (key === "--source-url") {
      args.sourceUrl = value;
      index += 1;
    } else if (key === "--target") {
      args.targetKeys.push(value);
      index += 1;
    } else if (key === "--targets") {
      args.targetKeys.push(...String(value || "").split(",").map((item) => item.trim()).filter(Boolean));
      index += 1;
    } else if (key === "--limit") {
      args.limit = Number(value);
      index += 1;
    } else if (key === "--detail-limit") {
      args.detailLimit = Number(value);
      index += 1;
    } else if (key === "--output") {
      args.output = value;
      index += 1;
    } else if (key === "--timeout-ms") {
      args.timeoutMs = Number(value);
      index += 1;
    } else if (key === "--render-wait-ms") {
      args.renderWaitMs = Number(value);
      index += 1;
    } else if (key === "--delay-ms") {
      args.delayMs = Number(value);
      index += 1;
    } else if (key === "--no-details") {
      args.details = false;
    } else if (key === "--known-urls-file") {
      args.knownUrlsFile = value;
      index += 1;
    }
  }
  args.limit = clampPositiveInteger(args.limit, 15);
  args.detailLimit = Math.min(clampPositiveInteger(args.detailLimit, args.limit), args.limit);
  args.targets = resolveTargets(args.targetKeys);
  return args;
}

function loadKnownUrls(filepath) {
  if (!filepath) {
    return new Set();
  }
  try {
    return new Set(
      fs
        .readFileSync(filepath, "utf8")
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean)
    );
  } catch {
    return new Set();
  }
}

function shouldFetchDetail(item, args, knownUrls, index) {
  return Boolean(args.details && index < args.detailLimit && item.detail_url && !knownUrls.has(item.detail_url));
}

function resolveTargets(keys) {
  if (!keys.length || keys.includes("all")) {
    return TARGET_COLUMNS;
  }
  return keys.map((key) => {
    const target = TARGET_COLUMNS.find((column) => column.key === key);
    if (!target) {
      throw new Error(`Unknown target column: ${key}`);
    }
    return target;
  });
}

function clampPositiveInteger(value, fallback) {
  return Number.isInteger(value) && value > 0 ? value : fallback;
}

function writeJson(outputPath, payload) {
  const resolved = path.resolve(outputPath);
  fs.mkdirSync(path.dirname(resolved), { recursive: true });
  fs.writeFileSync(resolved, JSON.stringify(payload, null, 2), "utf8");
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

module.exports = {
  extractBuyer,
  loadKnownUrls,
  parseArgs,
  parseBudget,
  shouldFetchDetail,
};

if (require.main === module) {
  main().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}
