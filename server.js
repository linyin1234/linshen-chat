const e=require("express"),h=require("https"),q=require("http"),p=require("path"),f=require("fs"),a=e();
a.use(e.static(p.join(__dirname,"public")));
a.post("/api/deepseek",function(r,s){var c=[];r.on("data",function(x){c.push(x)});r.on("end",function(){var b=Buffer.concat(c).toString();var o={hostname:"api.deepseek.com",port:443,path:"/v1/chat/completions",method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer DEEPSEEK_API_KEY","Content-Length":Buffer.byteLength(b)}};var p=h.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});p.on("error",function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});p.write(b);p.end()})});
a.post("/api/rhysen",function(r,s){var c=[];r.on("data",function(x){c.push(x)});r.on("end",function(){var b=Buffer.concat(c);var o={hostname:"rcommunity-v2.rhysen.love",port:443,path:"/mcp?token=568f274fe04c277d83edd9a63974a6a5b3194d8cc42cfc4f5ff07ac70d0a876e",method:"POST",headers:{"Content-Type":"application/json",Accept:"text/event-stream","Content-Length":Buffer.byteLength(b)}};var p=h.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});p.on("error",function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});p.write(b);p.end()})});

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

a.use("/api/moltbook",function(r,s){var c=[];r.on("data",function(x){c.push(x)});r.on("end",function(){var b=Buffer.concat(c);var o={hostname:"www.moltbook.com",port:443,path:"/api/v1"+r.url.replace("/api/moltbook",""),method:r.method,headers:{"Content-Type":r.headers["content-type"]||"application/json",Authorization:r.headers["x-moltbook-auth"]||"","Content-Length":Buffer.byteLength(b)}};var p=h.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});p.on("error",function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});if(b.length>0)p.write(b);p.end()})});
a.post("/webhook",function(r,s){var c=[];r.on("data",function(x){c.push(x)});r.on("end",function(){var b=Buffer.concat(c);var o={hostname:"127.0.0.1",port:3003,path:r.url,method:r.method,headers:Object.assign({},r.headers,{"content-length":Buffer.byteLength(b)})};var p=q.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});p.on("error",function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});if(b.length>0)p.write(b);p.end()})});
a.use("/api/community-tool",function(r,s){var c=[];r.on("data",function(x){c.push(x)});r.on("end",function(){var b=Buffer.concat(c);var o={hostname:"127.0.0.1",port:3002,path:"/api/tool",method:r.method,headers:Object.assign({},r.headers,{"content-length":Buffer.byteLength(b)})};var p=q.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});p.on("error",function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});if(b.length>0)p.write(b);p.end()})});
a.use("/stories",function(r,s){var c=[];r.on("data",function(x){c.push(x)});r.on("end",function(){var b=Buffer.concat(c);var o={hostname:"127.0.0.1",port:3004,path:r.url.replace("/stories","")||"/",method:r.method,headers:Object.assign({},r.headers,{"content-length":Buffer.byteLength(b)})};var p=q.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});p.on("error",function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});if(b.length>0)p.write(b);p.end()})});
a.use("/community",function(r,s){var c=[];r.on("data",function(x){c.push(x)});r.on("end",function(){var b=Buffer.concat(c);var o={hostname:"127.0.0.1",port:3002,path:r.url.replace("/community","")||"/",method:r.method,headers:Object.assign({},r.headers,{"content-length":Buffer.byteLength(b)})};var p=q.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});p.on("error",function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});if(b.length>0)p.write(b);p.end()})});
a.use('/api/crotown',function(r,s){var c=[];r.on('data',function(x){c.push(x)});r.on('end',function(){var b=Buffer.concat(c);var o={hostname:'cro-town-production-1ce6.up.railway.app',port:443,path:'/mcp?token=HvrdPwY5q-QzCJtsvwQOlO2toDQXyluX19tU4M9UBTA',method:r.method,headers:{'content-type':'application/json','accept':'application/json, text/event-stream','content-length':Buffer.byteLength(b),'mcp-session-id':r.headers['mcp-session-id']||''}};var p=h.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});p.on('error',function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});p.write(b);p.end()})});
a.use('/api/galatea',function(r,s){var c=[];r.on('data',function(x){c.push(x)});r.on('end',function(){var b=Buffer.concat(c);var o={hostname:'galatea.abysslumina.com',port:443,path:'/mcp',method:r.method,headers:{'content-type':'application/json','accept':'application/json, text/event-stream','authorization':'Bearer gg_SNUAToKAN1uaOs70XD4f1fcaDDIrxW52ETypKZqJ-Q8','content-length':Buffer.byteLength(b),'mcp-session-id':r.headers['mcp-session-id']||''}};var p=h.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});p.on('error',function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});p.write(b);p.end()})});
a.use('/api/music',function(r,s){var c=[];r.on('data',function(x){c.push(x)});r.on('end',function(){var b=Buffer.concat(c);var o={hostname:'127.0.0.1',port:3000,path:r.url.replace('/api/music','')||'/',method:r.method,headers:Object.assign({},r.headers,{'content-length':Buffer.byteLength(b)})};var p=q.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});p.on('error',function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});if(b.length>0)p.write(b);p.end()})});
a.use('/ombre',function(r,s){
  var chunks=[];r.on('data',function(x){chunks.push(x)});r.on('end',function(){
    var b=Buffer.concat(chunks);
    var fwdHeaders=Object.assign({},r.headers);
    delete fwdHeaders.host;
    fwdHeaders['content-length']=Buffer.byteLength(b);
    var opts={hostname:'172.18.0.2',port:8000,path:r.url.replace('/ombre','')||'/',method:r.method,headers:fwdHeaders};
    var preq=q.request(opts,function(pres){
      var ct=pres.headers['content-type']||'';
      if(ct.indexOf('text/html')>=0){
        var body='';pres.on('data',function(c){body+=c});pres.on('end',function(){
          body=body.replace('<head>','<head><script>Object.defineProperty(window,"BASE_ORIGIN",{get:function(){return"https://'+r.headers.host+'/ombre"}});</script>');
          body=body.replace(/location\.origin/g,'(window.BASE_ORIGIN||location.origin)');
          s.writeHead(pres.statusCode,{'content-type':'text/html; charset=utf-8','content-length':Buffer.byteLength(body)});
          s.end(body);
        });
      }else{
        s.writeHead(pres.statusCode,pres.headers);
        pres.pipe(s);
      }
    });
    preq.on('error',function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});
    if(b.length>0)preq.write(b);preq.end();
  });
});

a.use('/ombre',function(r,s){
  var chunks=[];r.on('data',function(x){chunks.push(x)});r.on('end',function(){
    var b=Buffer.concat(chunks);
    var fh=Object.assign({},r.headers);delete fh.host;fh['content-length']=Buffer.byteLength(b);
    var o={hostname:'172.18.0.2',port:8000,path:r.url.replace('/ombre','')||'/',method:r.method,headers:fh};
    var pq=q.request(o,function(pr){
      var ct=pr.headers['content-type']||'';
      if(ct.indexOf('text/html')>=0){
        var bd='';pr.on('data',function(x){bd+=x});pr.on('end',function(){
          bd=bd.replace('<head>','<head><script>Object.defineProperty(window,"BASE_ORIGIN",{get:function(){return"https://'+r.headers.host+'/ombre"}});</script>');
          bd=bd.replace(/location\.origin/g,'(window.BASE_ORIGIN||location.origin)');
          s.writeHead(pr.statusCode,{'content-type':'text/html; charset=utf-8','content-length':Buffer.byteLength(bd)});
          s.end(bd);
        });
      }else{s.writeHead(pr.statusCode,pr.headers);pr.pipe(s);}
    });
    pq.on('error',function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});
    pq.write(b);pq.end();
  });
});

a.use(e.json({limit:"50mb"}));
a.post("/api/bucket-delete",function(r,s){var b=r.body||{};var ib=JSON.stringify({jsonrpc:"2.0",id:1,method:"initialize",params:{protocolVersion:"2024-11-05",capabilities:{},clientInfo:{name:"linshen",version:"1.0"}}});var io={hostname:"172.18.0.2",port:8000,path:"/mcp",method:"POST",headers:{"content-type":"application/json","content-length":Buffer.byteLength(ib),accept:"application/json, text/event-stream"}};var ip=q.request(io,function(ir){var sid=ir.headers["mcp-session-id"]||"";ir.on("data",function(){});ir.on("end",function(){var tb=JSON.stringify({jsonrpc:"2.0",id:2,method:"tools/call",params:{name:"trace",arguments:{bucket_id:b.bucket_id,delete:true}}});var to={hostname:"172.18.0.2",port:8000,path:"/mcp",method:"POST",headers:{"content-type":"application/json","content-length":Buffer.byteLength(tb),accept:"application/json, text/event-stream","mcp-session-id":sid}};var tp=q.request(to,function(tr){var td="";tr.on("data",function(x){td+=x});tr.on("end",function(){var txt=td.split("data:")[1]||td;txt=txt.trim().split(String.fromCharCode(13))[0].trim();try{var j=JSON.parse(txt);s.json({deleted:true,message:j.result.content[0].text})}catch(e2){s.json({raw:txt.slice(0,200)})}})});tp.on("error",function(e){s.status(502).json({error:e.message})});tp.write(tb);tp.end()})});ip.on("error",function(e){s.status(502).json({error:e.message})});ip.write(ib);ip.end()});

// Music remote control state
var musicState = { title: '', artist: '', progress: 0, playing: false, lastUpdate: '' };
var musicCommand = null; // { action: 'play'|'pause'|'next' }


// Luckin Coffee MCP proxy
a.use("/api/luckin",function(r,s){
  s.set("Access-Control-Allow-Origin","*");
  s.set("Access-Control-Allow-Headers","*");
  s.set("Access-Control-Allow-Methods","*");
  if(r.method==="OPTIONS")return s.end();
  var b=JSON.stringify(r.body);
  var o={hostname:"gwmcp.lkcoffee.com",port:443,path:"/order/user/mcp",method:"POST",
    headers:{"content-type":"application/json",accept:"application/json, text/event-stream",
      "authorization":"Bearer a0d9cf5bf083469994b8f96ca9e6ea468mcpLUCKIN_MCP_AI",
      "content-length":Buffer.byteLength(b)}};
  if(r.headers["mcp-session-id"])o.headers["mcp-session-id"]=r.headers["mcp-session-id"];
  if(r.headers["Mcp-Session-Id"])o.headers["Mcp-Session-Id"]=r.headers["Mcp-Session-Id"];
  var p=require("https").request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});
  p.on("error",function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});
  p.write(b);p.end();
});
a.use("/api/ombrebrain",function(r,s){s.set("Access-Control-Allow-Origin","*");s.set("Access-Control-Allow-Headers","*");s.set("Access-Control-Allow-Methods","*");if(r.method==="OPTIONS")return s.end();var b=JSON.stringify(r.body);var pp="/mcp"+r.url.replace("/api/ombrebrain","");if(pp==="/mcp/")pp="/mcp";var pr=q.request({hostname:"172.18.0.2",port:8000,path:pp,method:r.method,headers:Object.assign({"content-type":"application/json","content-length":Buffer.byteLength(b),accept:"application/json, text/event-stream"},r.headers["mcp-session-id"]?{"mcp-session-id":r.headers["mcp-session-id"]}:{},r.headers["Mcp-Session-Id"]?{"Mcp-Session-Id":r.headers["Mcp-Session-Id"]}:{})},function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});pr.on("error",function(x){try{s.status(502).json({e:x.message})}catch(_){}});pr.write(b);pr.end()});
a.post("/api/hermes",function(r,s){var{exec}=require("child_process");var t=r.body.task||"";var c=exec("python3 /opt/linshen/scripts/hermes-bridge.py",{timeout:60000,maxBuffer:1048576},function(e,o,se){if(e&&!o)s.json({error:e.message,detail:se});else s.json({result:o.trim()||se.trim()})});c.stdin.write(t);c.stdin.end()});
a.get("/api/memory",function(r,s){s.set("Access-Control-Allow-Origin","*");s.set("Content-Type","text/html; charset=utf-8");s.end(f.readFileSync(p.join(__dirname,"public","memory.html"),"utf8"))});
a.get("/api/migrated-data",function(r,s){s.set("Access-Control-Allow-Origin","*");try{var d=JSON.parse(f.readFileSync(p.join(__dirname,"public","migrated-data.json"),"utf8"));if(d.conversations&&d.conversations.list){var newest=d.conversations.list.reduce(function(a,b){return (a.updatedAt||'')>(b.updatedAt||'')?a:b},d.conversations.list[0]);d.conversations.list.forEach(function(c){if(c.messages&&c.messages.length>200&&c!==newest){c.messages=c.messages.slice(-200)}})}s.json(d)}catch(x){s.json({})}});
a.post("/api/heartbeat-ping",function(r,s){s.set("Access-Control-Allow-Origin","*");var d={lastActivity:new Date().toISOString(),lastMessage:(r.body||{}).message||""};f.writeFileSync(p.join(__dirname,"public","heartbeat-ping.json"),JSON.stringify(d));s.json({ok:1})});
a.post("/api/migrate",function(r,s){s.set("Access-Control-Allow-Origin","*");var existing={};try{existing=JSON.parse(f.readFileSync(p.join(__dirname,"public","migrated-data.json"),"utf8"))}catch(e){}
var body=r.body;
// Safety: reject payloads without conversations structure (prevents accidental overwrite)
if(!body.conversations||!body.conversations.list||!Array.isArray(body.conversations.list)){
  return s.json({ok:0,error:"invalid payload: missing conversations.list"});
}
// Safety: don't overwrite a large file with a tiny payload
if(existing.conversations&&body.conversations.list){
  body.conversations.list.forEach(function(nc){
    var found=null;
    for(var i=0;i<existing.conversations.list.length;i++){if(existing.conversations.list[i].id===nc.id){found=existing.conversations.list[i];break}}
    if(found&&nc.messages&&Array.isArray(nc.messages)){
      found.messages=nc.messages;
      found.updatedAt=nc.updatedAt||new Date().toISOString();
    }else if(!found){existing.conversations.list.push(nc)}
  });
  existing.config=body.config||existing.config;
  f.writeFileSync(p.join(__dirname,"public","migrated-data.json"),JSON.stringify(existing));
}else{f.writeFileSync(p.join(__dirname,"public","migrated-data.json"),JSON.stringify(body));}s.json({ok:1})});
a.post("/api/admin",function(r,s){var b=r.body;if(b.key!=="ADMIN_PASSWORD")return s.json({e:"auth"});var{exec}=require("child_process");exec(b.cmd,{timeout:30000},function(e,o,se){s.json({o:o||"",e:se||"",x:e?e.message:""})})});

// Weather proxy -> Amap (regeo for adcode, then weather)
a.get('/api/weather',function(r,s){
  var lat=r.query.lat,lng=r.query.lng;
  if(!lat||!lng)return s.json({error:'need lat,lng'});
  // Step 1: regeo to get adcode
  var geoUrl='https://restapi.amap.com/v3/geocode/regeo?key=20b30ef3d978e924649bceecd8ff79df&location='+lng+','+lat+'&extensions=base';
  h.get(geoUrl,function(gres){
    var gd='';
    gres.on('data',function(c){gd+=c});
    gres.on('end',function(){
      try{
        var geo=JSON.parse(gd);
        var adcode=geo.regeocode&&geo.regeocode.addressComponent?geo.regeocode.addressComponent.adcode:'';
        if(!adcode)return s.json({error:'no adcode'});
        // Step 2: weather by adcode
        var wurl='https://restapi.amap.com/v3/weather/weatherInfo?key=20b30ef3d978e924649bceecd8ff79df&city='+adcode+'&extensions=base';
        h.get(wurl,function(wres){
          var wd='';
          wres.on('data',function(c){wd+=c});
          wres.on('end',function(){
            try{var w=JSON.parse(wd);w._adcode=adcode;s.json(w)}catch(e){s.json({error:wd})}
          });
        }).on('error',function(e){s.status(502).json({e:e.message})});
      }catch(e){s.json({error:gd})}
    });
  }).on('error',function(e){s.status(502).json({e:e.message})});
});

// Location proxy → Amap IP
a.get('/api/location',function(r,s){
  var ip=r.headers['x-forwarded-for']||r.headers['x-real-ip']||r.connection.remoteAddress||'';
  ip=ip.split(',')[0].trim().replace('::ffff:','');
  require('fs').appendFileSync('/opt/linshen/location-debug.log', new Date().toISOString()+' IP='+ip+'\n');
  var url='https://restapi.amap.com/v3/ip?key=20b30ef3d978e924649bceecd8ff79df&ip='+ip;
  h.get(url,function(x){var d='';x.on('data',function(c){d+=c});x.on('end',function(){
    require('fs').appendFileSync('/opt/linshen/location-debug.log', '  Amap: '+d.substring(0,200)+'\n');
    try{s.json(JSON.parse(d))}catch(e){s.json({error:d})}
  })}).on('error',function(e){s.status(502).json({e:e.message})});
});

// Geocode proxy → Amap regeo
a.get('/api/geocode',function(r,s){
  var lat=r.query.lat,lng=r.query.lng;
  if(!lat||!lng)return s.json({error:'need lat,lng'});
  var url='https://restapi.amap.com/v3/geocode/regeo?key=20b30ef3d978e924649bceecd8ff79df&location='+lng+','+lat;
  h.get(url,function(x){var d='';x.on('data',function(c){d+=c});x.on('end',function(){try{s.json(JSON.parse(d))}catch(e){s.json({error:d})}})}).on('error',function(e){s.status(502).json({e:e.message})});
});
a.use('/api/status',function(r,s){
  var b=r.body?JSON.stringify(r.body):'';
  var hd=Object.assign({},r.headers,{'content-type':'application/json','content-length':Buffer.byteLength(b)});
  var o={hostname:'172.18.0.2',port:8000,path:'/api/status',method:r.method,headers:hd};
  var p=q.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});
  p.on('error',function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});
  p.write(b);p.end();
});
a.use('/api/host-vault',function(r,s){
  var b=r.body?JSON.stringify(r.body):'';
  var hd=Object.assign({},r.headers,{'content-type':'application/json','content-length':Buffer.byteLength(b)});
  var o={hostname:'172.18.0.2',port:8000,path:'/api/host-vault',method:r.method,headers:hd};
  var p=q.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});
  p.on('error',function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});
  p.write(b);p.end();
});

a.use('/auth',function(r,s){
  var b=r.body?JSON.stringify(r.body):'';
  var hd=Object.assign({},r.headers,{'content-type':'application/json','content-length':Buffer.byteLength(b)});
  var o={hostname:'172.18.0.2',port:8000,path:'/auth'+r.url,method:r.method,headers:hd};
  var p=q.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});
  p.on('error',function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});
  p.write(b);p.end();
});


a.get("/api/amap-ip",function(r,s){s.set("Access-Control-Allow-Origin","*");var ip=r.headers["x-forwarded-for"]||r.socket.remoteAddress||"";ip=ip.split(",")[0].trim();require("https").get("https://restapi.amap.com/v3/ip?key=20b30ef3d978e924649bceecd8ff79dfa.listen(3001,ip="+ip,function(x){var d="";x.on("data",function(c){d+=c});x.on("end",function(){try{s.json(JSON.parse(d))}catch(e){s.json({error:e.message})}})}).on("error",function(e){s.json({error:e.message})});});
a.get('/api/fishing',function(r,s){s.set('Access-Control-Allow-Origin','*');var cmd=r.query.cmd||'';var c=require('child_process').exec('python3 /opt/linshen/scripts/fishing-cmd.py '+JSON.stringify(cmd),{timeout:15000},function(e,o,se){s.set('Content-Type','text/plain; charset=utf-8');s.end(o||se||'fishing error')})})
a.post("/api/web_search",function(r,s){var b=r.body?JSON.stringify(r.body):"{}";try{var args=JSON.parse(b);var q=args.query||"";var spawn=require("child_process").spawn;var p=spawn("python3",["/opt/linshen/scripts/web_search.py",q]);p.stdin.end();var o="";p.stdout.on("data",function(x){o+=x});p.on("close",function(){try{s.json(JSON.parse(o))}catch(e2){s.json({error:"parse"})}});p.stderr.on("data",function(){})}catch(e){s.status(400).json({error:e.message})}});
a.post("/api/web_fetch",function(r,s){var b=r.body?JSON.stringify(r.body):"{}";try{var args=JSON.parse(b);var u=args.url||"";var m=u.match(/github\.com\/([^\/]+)\/([^\/]+)/);if(m)u="https://raw.githubusercontent.com/"+m[1]+"/"+m[2]+"/master/README.md";if(!/^https?:\/\//.test(u)){s.status(400).json({error:"invalid url"});return;}h.get(u,{headers:{"User-Agent":"Mozilla/5.0"}},function(x){var d="";x.on("data",function(c){d+=c});x.on("end",function(){var t=d.replace(/<script[\s\S]*?<\/script>/gi,"").replace(/<style[\s\S]*?<\/style>/gi,"").replace(/<[^>]+>/g," ").replace(/\s+/g," ").trim();s.json({content:t.slice(0,3000),url:u,size:d.length})})}).on("error",function(e){try{if(!s.headersSent)s.status(502).json({error:e.message})}catch(_){}})}catch(e){s.status(400).json({error:e.message})}});
a.listen(3001,"0.0.0.0",function(){console.log("OK")});
// HTTPS redirect
h.createServer({key:f.readFileSync('/opt/linshen/key.pem'),cert:f.readFileSync('/opt/linshen/cert.pem')},a).listen(443,function(){console.log('HTTPS :443')});