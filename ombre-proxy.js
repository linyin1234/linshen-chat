const http = require('http');
module.exports = function(app) {
  app.use('/api/ombrebrain', (req, res) => {
    try {
      const body = JSON.stringify(req.body);
      let p = '/mcp' + req.url.replace('/api/ombrebrain','');
      if (p === '/mcp/') p = '/mcp';
      const pr = http.request({
        hostname: '127.0.0.1', port: 8000,
        path: p, method: req.method,
        headers: { 'content-type': 'application/json', 'content-length': Buffer.byteLength(body), 'accept': 'application/json, text/event-stream' }
      }, prRes => { res.writeHead(prRes.statusCode, prRes.headers); prRes.pipe(res); });
      pr.on('error', e => { res.status(502).json({error:e.message}); });
      pr.write(body);
      pr.end();
    } catch(e) { res.status(500).json({error:e.message}); }
  });
};