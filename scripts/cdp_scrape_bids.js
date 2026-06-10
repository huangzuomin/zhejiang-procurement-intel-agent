#!/usr/bin/env node
"use strict";
/**
 * Scrape bids from zfcg page via CDP and save to file.
 * Connects to browser via CDP, navigates to bid list, 
 * auto-paginates, collects all data, saves to JSON.
 */
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');
const http = require('http');

const OUT = path.resolve(__dirname, '../data/latest_bids.json');
const DATE = '2026-06-09';

function cdpSend(ws, method, params) {
  return new Promise((resolve, reject) => {
    const id = Math.floor(Math.random() * 1e9);
    const handler = (raw) => {
      const msg = JSON.parse(raw.toString());
      if (msg.id === id) {
        ws.off('message', handler);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      }
    };
    ws.on('message', handler);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  // Find zfcg page
  const targets = await new Promise((resolve, reject) => {
    http.get('http://127.0.0.1:18800/json', (res) => {
      let d = ''; res.on('data', c => d += c); res.on('end', () => resolve(JSON.parse(d)));
    }).on('error', reject);
  });
  const page = targets.find(t => t.url && t.url.includes('zfcg'));
  if (!page) { console.error('No zfcg page'); process.exit(1); }
  console.log('Connecting to:', page.url);

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.on('open', resolve); ws.on('error', reject); });

  // Navigate to bid announcement page with date filter
  // The page should already be there, but let's ensure
  console.log('Navigating to bid list...');

  // Run the full scrape via evaluate
  const scrapeScript = `
    async () => {
      // Click on bid announcement tree node if needed
      const nodes = [...document.querySelectorAll('.po-tree-node')];
      const parent = nodes.find(n => {
        const label = n.querySelector('.po-tree-node__label');
        return label && label.textContent.replace(/\\s+/g, '') === '采购项目公告';
      });
      if (parent) {
        const exp = parent.querySelector('.po-tree-node__expand-icon');
        if (exp && parent.getAttribute('aria-expanded') !== 'true') {
          exp.click();
          await new Promise(r => setTimeout(r, 1500));
        }
        const children = parent.querySelectorAll('.po-tree-node .po-tree-node__content');
        for (const c of children) {
          if (c.textContent.replace(/\\s+/g, '') === '招标公告') {
            c.click();
            await new Promise(r => setTimeout(r, 3000));
            break;
          }
        }
      }
      
      // Set date filter
      const inputs = document.querySelectorAll('input');
      let startDate, endDate, searchBtn;
      inputs.forEach(i => {
        if (i.placeholder?.includes('开始') || i.placeholder?.includes('结束')) {
          // Use nativeInputValueSetter to set value
          const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          if (i.placeholder.includes('开始')) { nativeSetter.call(i, '${DATE}'); startDate = i; }
          if (i.placeholder.includes('结束')) { nativeSetter.call(i, '${DATE}'); endDate = i; }
          i.dispatchEvent(new Event('input', { bubbles: true }));
          i.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });
      
      // Click search
      document.querySelectorAll('button').forEach(b => {
        if (b.textContent.trim() === '搜索') { b.click(); searchBtn = b; }
      });
      if (searchBtn) await new Promise(r => setTimeout(r, 2000));
      
      // Scrape all pages
      const all = [];
      const seen = new Set();
      let pages = 0;
      
      while (true) {
        pages++;
        const items = document.querySelectorAll('.search-list ul.list li');
        let todayCount = 0;
        
        items.forEach((li) => {
          const a = li.querySelector('a');
          if (!a) return;
          const text = li.textContent;
          const dm = text.match(/(\\d{4}-\\d{2}-\\d{2})/);
          if (!dm || dm[1] !== '${DATE}') return;
          const url = a.href;
          if (seen.has(url)) return;
          seen.add(url);
          all.push({
            region: text.match(/^\\[([^·\\]]+)/)?.[1]?.trim() || '',
            category: text.match(/·([^\\]]+)\\]/)?.[1]?.trim() || '',
            title: a.textContent.trim(),
            url: url,
            date: dm[1]
          });
          todayCount++;
        });
        
        const btn = document.querySelector('.btn-next');
        if (!btn || btn.disabled || btn.classList.contains('disabled') || todayCount === 0) break;
        btn.click();
        await new Promise(r => setTimeout(r, 1800));
      }
      
      return { count: all.length, pages, data: all };
    }
  `;

  console.log('Starting scrape...');
  const result = await cdpSend(ws, 'Runtime.evaluate', {
    expression: `(${scrapeScript})()`,
    returnByValue: true,
    awaitPromise: true
  });

  const value = result?.result?.value;
  if (!value || !value.data) {
    console.error('Scrape failed:', JSON.stringify(result).slice(0, 500));
    process.exit(1);
  }

  const bids = value.data;
  // Expand short keys to full keys
  const expanded = bids.map(b => ({
    region: b.region || b.r || '',
    category: b.category || b.c || '',
    title: b.title || b.t || '',
    url: b.url || b.u || '',
    date: b.date || b.d || DATE
  }));

  fs.writeFileSync(OUT, JSON.stringify(expanded, null, 2));
  console.log(`Saved ${expanded.length} bids to ${OUT}`);
  ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
