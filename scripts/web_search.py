import sys, json, urllib.request

q = sys.argv[1] if len(sys.argv) > 1 else ""
url = "http://127.0.0.1:8888/search?q=" + urllib.request.quote(q) + "&format=json&language=zh-CN"
try:
    with urllib.request.urlopen(url, timeout=15) as r:
        data = json.loads(r.read())
except Exception as e:
    print(json.dumps({"results": [], "error": str(e)}))
    sys.exit(0)

results = []
for item in data.get("results", [])[:8]:
    results.append({
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "snippet": (item.get("content", "") or "")[:300]
    })
print(json.dumps({"results": results}, ensure_ascii=False))
