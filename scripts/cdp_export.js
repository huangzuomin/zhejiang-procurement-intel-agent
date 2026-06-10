#!/usr/bin/env node
"use strict";
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');
const http = require('http');

const OUT = path.resolve(__dirname, '../data/latest_bids.json');
const WS_URL = process.argv[2]; // ws://... from browser tabs
const EXPR = process.argv[3] || 'JSON.stringify(window._bidAll)';

if (!WS_URL) {
  // Get the page's wsUrl from CDP
  http.get('http://127.0.0.1:18800/json', (res) => {
    let d = '';
    res.on('data', c => d += c);
    res.on('end', () => {
      const targets = JSON.parse(d);
      const page = targets.find(t => t.url && t.url.includes('zfcg'));
      if (!page) { console.error('No zfcg page found'); process.exit(1); }
      console.log('Found:', page.url);
      run(page.webSocketDebuggerUrl);
    });
  }).on('error', e => { console.error(e); process.exit(1); });
} else {
  run(WS_URL);
}

function run(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let id = 1;
  const pending = {};

  ws.on('open', () => {
    ws.send(JSON.stringify({ id: id++, method: 'Runtime.evaluate', params: { expression: EXPR, returnByValue: true, awaitPromise: true } }));
  });

  ws.on('message', (raw) => {
    const msg = JSON.parse(raw.toString());
    if (msg.id && pending[msg.id]) {
      pending[msg.id](msg);
      delete pending[msg.id];
      ws.close();
    }
    if (msg.id === 1) {
      const result = msg.result?.result?.value;
      if (result) {
        const data = JSON.parse(result);
        fs.writeFileSync(OUT, JSON.stringify(data, null, 2));
        console.log('Exported', data.length, 'bids to', OUT);
      } else {
        console.error('No result:', JSON.stringify(msg.result).slice(0, 500));
      }
    }
  });

  ws.on('error', (e) => console.error('WS error:', e.message));
  ws.on('close', () => process.exit(0));
}
