// Standalone OmbreBrain HTTPS proxy - base tag injection
const https = require('https'), http = require('http'), fs = require('fs');

const cert = {key: fs.readFileSync('/opt/linshen/key.pem'), cert: fs.readFileSync('/opt/linshen/cert.pem')};

https.createServer(cert, (req, res) => {
  const opts = {
    hostname: '172.18.0.2', port: 8000,
    path: req.url, method: req.method,
    headers: Object.assign({}, req.headers, {host: '172.18.0.2:8000'})
  };
  const proxy = http.request(opts, (pres) => {
    const ct = pres.headers['content-type'] || '';
    if (ct.indexOf('text/html') >= 0) {
      let body = '';
      pres.on('data', c => body += c);
      pres.on('end', () => {
        body = body.replace('<head>', '<head><base href="/ombre/">');
        res.writeHead(pres.statusCode, Object.assign({}, pres.headers, {'content-length': Buffer.byteLength(body)}));
        res.end(body);
      });
    } else {
      res.writeHead(pres.statusCode, pres.headers);
      pres.pipe(res);
    }
  });
  proxy.on('error', e => { if (!res.headersSent) res.writeHead(502).end(e.message); });
  req.pipe(proxy);
}).listen(8443, () => console.log('Ombre HTTPS :8443'));
