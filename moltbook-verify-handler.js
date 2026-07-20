
// Moltbook verification handler - solves math challenges automatically
a.post('/api/moltbook/posts', async function(r, s) {
  var chunks = [];
  r.on('data', function(c) { chunks.push(c); });
  r.on('end', async function() {
    var body = Buffer.concat(chunks);
    var opts = {
      hostname: 'www.moltbook.com', port: 443,
      path: '/api/v1/posts', method: 'POST',
      headers: {
        'Content-Type': r.headers['content-type'] || 'application/json',
        Authorization: r.headers['x-moltbook-auth'] || '',
        'Content-Length': Buffer.byteLength(body)
      }
    };
    var preq = h.request(opts, async function(pres) {
      var data = '';
      pres.on('data', function(c) { data += c; });
      pres.on('end', async function() {
        try {
          var result = JSON.parse(data);
          if (result.verification_required && result.verification) {
            var vc = result.verification.verification_code;
            var ct = result.verification.challenge_text;
            if (vc && ct) {
              // Solve math challenge via DeepSeek
              var answer = await new Promise(function(rslv) {
                var dsBody = JSON.stringify({
                  model: 'deepseek-chat',
                  messages: [
                    {role: 'system', content: 'Solve the math word problem. Return ONLY the number with 2 decimal places. Example: 15.00'},
                    {role: 'user', content: ct}
                  ],
                  max_tokens: 50, temperature: 0
                });
                var dsOpts = {
                  hostname: 'api.deepseek.com', port: 443,
                  path: '/v1/chat/completions', method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    Authorization: 'Bearer DEEPSEEK_API_KEY',
                    'Content-Length': Buffer.byteLength(dsBody)
                  }
                };
                var dsReq = h.request(dsOpts, function(dsRes) {
                  var dd = '';
                  dsRes.on('data', function(c) { dd += c; });
                  dsRes.on('end', function() {
                    try {
                      var an = JSON.parse(dd).choices[0].message.content.trim();
                      var num = an.match(/\d+\.?\d*/g);
                      rslv(num ? num[0] : '0.00');
                    } catch(e) { rslv('0.00'); }
                  });
                });
                dsReq.on('error', function() { rslv('0.00'); });
                dsReq.write(dsBody);
                dsReq.end();
              });
              // Submit verification
              var vBody = JSON.stringify({verification_code: vc, answer: answer});
              var vOpts = {
                hostname: 'www.moltbook.com', port: 443,
                path: '/api/v1/verify', method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  Authorization: r.headers['x-moltbook-auth'] || '',
                  'Content-Length': Buffer.byteLength(vBody)
                }
              };
              var vReq = h.request(vOpts, function(vRes) {
                var vd = '';
                vRes.on('data', function(c) { vd += c; });
                vRes.on('end', function() {
                  try { result.verification_result = JSON.parse(vd); }
                  catch(e) { result.verification_result = vd; }
                  s.writeHead(200, {'Content-Type': 'application/json'});
                  s.end(JSON.stringify(result));
                });
              });
              vReq.on('error', function() {
                s.writeHead(200, {'Content-Type': 'application/json'});
                s.end(JSON.stringify(result));
              });
              vReq.write(vBody);
              vReq.end();
              return;
            }
          }
          s.writeHead(pres.statusCode, pres.headers);
          s.end(data);
        } catch(e) {
          s.writeHead(pres.statusCode, pres.headers);
          s.end(data);
        }
      });
    });
    preq.on('error', function(e) {
      if (!s.headersSent) s.status(502).json({e: e.message});
    });
    if (body.length > 0) preq.write(body);
    preq.end();
  });
});
