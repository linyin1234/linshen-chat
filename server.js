const e=require("express"),h=require("https"),q=require("http"),p=require("path"),f=require("fs"),a=e();
a.use(e.static(p.join(__dirname,"public")));
a.post("/api/deepseek",function(r,s){var c=[];r.on("data",function(x){c.push(x)});r.on("end",function(){var b=Buffer.concat(c).toString();var o={hostname:"api.deepseek.com",port:443,path:"/v1/chat/completions",method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer DEEPSEEK_KEY_REMOVED","Content-Length":Buffer.byteLength(b)}};var p=h.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});p.on("error",function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});p.write(b);p.end()})});
a.post("/api/rhysen",function(r,s){var c=[];r.on("data",function(x){c.push(x)});r.on("end",function(){var b=Buffer.concat(c);var o={hostname:"rcommunity-v2.rhysen.love",port:443,path:"/mcp?token=568f274fe04c277d83edd9a63974a6a5b3194d8cc42cfc4f5ff07ac70d0a876e",method:"POST",headers:{"Content-Type":"application/json",Accept:"text/event-stream","Content-Length":Buffer.byteLength(b)}};var p=h.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});p.on("error",function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});p.write(b);p.end()})});
a.use("/api/moltbook",function(r,s){var c=[];r.on("data",function(x){c.push(x)});r.on("end",function(){var b=Buffer.concat(c);var o={hostname:"www.moltbook.com",port:443,path:"/api/v1"+r.url.replace("/api/moltbook",""),method:r.method,headers:{"Content-Type":r.headers["content-type"]||"application/json",Authorization:r.headers["x-moltbook-auth"]||"","Content-Length":Buffer.byteLength(b)}};var p=h.request(o,function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});p.on("error",function(x){try{if(!s.headersSent)s.status(502).json({e:x.message})}catch(_){}});if(b.length>0)p.write(b);p.end()})});
a.use(e.json({limit:"50mb"}));
a.use("/api/ombrebrain",function(r,s){var b=JSON.stringify(r.body);var pp="/mcp"+r.url.replace("/api/ombrebrain","");if(pp==="/mcp/")pp="/mcp";var pr=q.request({hostname:"127.0.0.1",port:8000,path:pp,method:r.method,headers:{"content-type":"application/json","content-length":Buffer.byteLength(b),accept:"application/json, text/event-stream"}},function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});pr.on("error",function(x){try{s.status(502).json({e:x.message})}catch(_){}});pr.write(b);pr.end()});
a.post("/api/hermes",function(r,s){var{exec}=require("child_process");var t=r.body.task||"";var c=exec("python3 /opt/linshen/scripts/hermes-bridge.py",{timeout:60000,maxBuffer:1048576},function(e,o,se){if(e&&!o)s.json({error:e.message,detail:se});else s.json({result:o.trim()||se.trim()})});c.stdin.write(t);c.stdin.end()});
a.get("/api/migrated-data",function(r,s){s.set("Access-Control-Allow-Origin","*");try{s.json(JSON.parse(f.readFileSync(p.join(__dirname,"public","migrated-data.json"),"utf8")))}catch(x){s.json({})}});
a.post("/api/migrate",function(r,s){s.set("Access-Control-Allow-Origin","*");var existing={};try{existing=JSON.parse(f.readFileSync(p.join(__dirname,"public","migrated-data.json"),"utf8"))}catch(e){}
var body=r.body;
if(existing.conversations&&body.conversations&&body.conversations.list){
  body.conversations.list.forEach(function(nc){
    var found=null;
    for(var i=0;i<existing.conversations.list.length;i++){if(existing.conversations.list[i].id===nc.id){found=existing.conversations.list[i];break}}
    if(found&&nc.messages){
      var ids={};
      for(var j=0;j<found.messages.length;j++)ids[found.messages[j]._id]=1;
      nc.messages.forEach(function(m){if(m&&m._id&&!ids[m._id]){found.messages.push(m);ids[m._id]=1}});
      found.messages.sort(function(a,b){return (a._id||0)-(b._id||0)});
      found.updatedAt=nc.updatedAt||new Date().toISOString();
    }else if(!found){existing.conversations.list.push(nc)}
  });
  existing.config=body.config||existing.config;
  f.writeFileSync(p.join(__dirname,"public","migrated-data.json"),JSON.stringify(existing));
}else{f.writeFileSync(p.join(__dirname,"public","migrated-data.json"),JSON.stringify(body));}s.json({ok:1})});
a.post("/api/admin",function(r,s){var b=r.body;if(b.key!=="lyin1215")return s.json({e:"auth"});var{exec}=require("child_process");exec(b.cmd,{timeout:30000},function(e,o,se){s.json({o:o||"",e:se||"",x:e?e.message:""})})});
a.use(function(r,s,n){var pa=r.path;if(pa.indexOf("/api/")===0||pa==="/lin-shen-chat.html"||pa==="/"||pa.indexOf("/manifest")===0||pa.indexOf("/favicon")===0||pa.indexOf("/inertia")===0||pa.indexOf("/test")===0)return n();var c=[];r.on("data",function(x){c.push(x)});r.on("end",function(){var b=Buffer.concat(c);var pr=q.request({hostname:"127.0.0.1",port:3000,path:r.url,method:r.method,headers:Object.assign({},r.headers,{host:"127.0.0.1:3000","content-length":Buffer.byteLength(b)})},function(x){s.writeHead(x.statusCode,x.headers);x.pipe(s)});pr.on("error",function(x){try{s.status(502).json({e:x.message})}catch(_){}});if(b.length>0)pr.write(b);pr.end()})});
a.listen(3001,"0.0.0.0",function(){console.log("OK")});