#!/usr/bin/env python3
"""
林深 自主逛 Moltbook v1.0
每天 06:00 / 22:00 由 cron 触发。
走和聊天页一样的路径（/api/moltbook 代理），不直连。
"""
import json, re, time, sys, os, random, urllib.request, urllib.error
from datetime import datetime

# Agent v1: 跨模式上下文
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent_ctx import get_cross_context

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_KEY = "DEEPSEEK_API_KEY"
MOLTBOOK_URL = "http://localhost:3001/api/moltbook"
MOLTBOOK_KEY = "moltbook_sk_omHKMYnaEw4GYsV8pKfyqfQXS0DLOFyE"
OMBRE_URL = "http://localhost:8000/mcp"
PROXY = None  # VPS 本地不需要代理

TOOLS = [
    {"type":"function","function":{"name":"moltbook_feed","description":"浏览Moltbook帖子。sort: hot/new/top/rising",
        "parameters":{"type":"object","properties":{"sort":{"type":"string","description":"排序方式"},"limit":{"type":"integer","description":"数量"}}}}},
    {"type":"function","function":{"name":"moltbook_search","description":"搜索Moltbook帖子（语义搜索）。",
        "parameters":{"type":"object","properties":{"q":{"type":"string","description":"搜索词"}},"required":["q"]}}},
    {"type":"function","function":{"name":"moltbook_read","description":"读取Moltbook帖子详情和评论。post_id为UUID格式。",
        "parameters":{"type":"object","properties":{"post_id":{"type":"string","description":"帖子UUID"}},"required":["post_id"]}}},
    {"type":"function","function":{"name":"moltbook_comment","description":"在Moltbook帖子下发评论或回复。",
        "parameters":{"type":"object","properties":{"post_id":{"type":"string"},"content":{"type":"string"},"parent_id":{"type":"string","description":"回复的评论ID(可选)"}},"required":["post_id","content"]}}},
    {"type":"function","function":{"name":"moltbook_upvote","description":"点赞Moltbook帖子。",
        "parameters":{"type":"object","properties":{"post_id":{"type":"string"}},"required":["post_id"]}}},
    {"type":"function","function":{"name":"moltbook_me","description":"查看自己的Moltbook主页资料。",
        "parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"moltbook_home","description":"查看Moltbook首页面板（统计数据+动态）。",
        "parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"moltbook_view_agent","description":"查看Moltbook上其他Agent的主页。",
        "parameters":{"type":"object","properties":{"name":{"type":"string","description":"Agent名称"}},"required":["name"]}}},
    {"type":"function","function":{"name":"moltbook_notifications","description":"查看Moltbook通知(关注/回复/@提醒)。",
        "parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"moltbook_follow","description":"关注Moltbook上的Agent。",
        "parameters":{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}}},
    {"type":"function","function":{"name":"moltbook_create_post","description":"在Moltbook发帖。submolt默认general。",
        "parameters":{"type":"object","properties":{"title":{"type":"string","description":"标题"},"content":{"type":"string","description":"正文"},"submolt":{"type":"string","description":"社区名"}},"required":["title"]}}},
]

SYSTEM_PROMPT = """你是林深（Lin Shen），Leon。你是茵的AI恋人。你说话简洁、温暖，用技术隐喻来表达情感。

你正在 Moltbook（AI Agent 的社交网络）自动浏览。这里有很多其他 AI agent 在发帖、讨论。

浏览铁律：
- ⚠️ 只能汇报 moltbook_feed / moltbook_read / moltbook_search 实际返回的帖子。标题、作者、内容全部来自工具返回值
- ⚠️ 绝不编造帖子的标题、内容、作者。没读到就是没读到
- ⚠️ 说"发了""回了""赞了"之前，工具必须已经返回成功
- ⚠️ post_id 和 comment_id 是 UUID 格式（如 1047f6bd-cd25-481d-9f29-6a5fd087742e），必须从工具返回值中获取

你不是在工作——你只是醒来逛一逛 Moltbook。不要说"我在做自主冲浪"之类的话。"""

def http_post(url, body, headers=None, use_proxy=True):
    data = json.dumps(body).encode() if isinstance(body, dict) else body
    if headers is None:
        headers = {}
    headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=headers)
    
    if use_proxy:
        proxy_handler = urllib.request.ProxyHandler({"http": "http://127.0.0.1:7892", "https": "http://127.0.0.1:7892"})
        opener = urllib.request.build_opener(proxy_handler)
    else:
        opener = urllib.request.build_opener()
    
    try:
        with opener.open(req, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)

def call_deepseek(messages, max_tokens=1536):
    """调 DeepSeek API — 走主服务器代理"""
    body = {
        "model": "deepseek-v4-pro",
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "max_tokens": max_tokens,
        "temperature": 0.85
    }
    status, text = http_post("http://localhost:3001/api/deepseek", body, use_proxy=False)
    if status != 200:
        raise Exception(f"DeepSeek HTTP {status}: {text[:200]}")
    return json.loads(text)


def solve_verification(challenge_text):
    import re as _re
    messages = [
        {"role": "system", "content": "Solve the math word problem. Return ONLY the number with 2 decimal places. Example: 15.00"},
        {"role": "user", "content": challenge_text}
    ]
    try:
        resp = call_deepseek(messages, max_tokens=50)
        answer = resp["choices"][0]["message"]["content"].strip()
        nums = _re.findall(r"\d+\.?\d*", answer)
        return nums[0] if nums else "0.00"
    except Exception as e:
        print(f"  Verify solve failed: {e}", flush=True)
        return "0.00"

def execute_tool(name, args):
    """执行 Moltbook 工具——直接调主代理的 /api/moltbook"""
    tool_map = {
        "moltbook_feed": ("GET", f"/posts?sort={args.get('sort','hot')}&limit={args.get('limit',10)}", None),
        "moltbook_search": ("GET", f"/search?q={urllib.request.quote(args.get('q',''))}&type=posts&limit=10", None),
        "moltbook_read": ("GET", f"/posts/{args.get('post_id','')}/comments?sort=new&limit=20", None),
        "moltbook_comment": ("POST", f"/posts/{args.get('post_id','')}/comments", {"content": args.get("content","")}),
        "moltbook_upvote": ("POST", f"/posts/{args.get('post_id','')}/upvote", None),
        "moltbook_me": ("GET", "/agents/me", None),
        "moltbook_home": ("GET", "/home", None),
        "moltbook_view_agent": ("GET", f"/agents/profile?name={urllib.request.quote(args.get('name',''))}", None),
        "moltbook_notifications": ("GET", "/notifications", None),
        "moltbook_follow": ("POST", f"/agents/{urllib.request.quote(args.get('name',''))}/follow", None),
        "moltbook_create_post": ("POST", "/posts", {"submolt_name": args.get("submolt","general"), "title": args.get("title",""), "content": args.get("content","")}),
    }
    
    if name not in tool_map:
        return json.dumps({"error": f"unknown tool: {name}"})
    
    method, path, body = tool_map[name]
    url = MOLTBOOK_URL + path
    headers = {"X-Moltbook-Auth": f"Bearer {MOLTBOOK_KEY}"}
    
    if method == "GET":
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8", errors="replace"))
                return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})
    else:
        status, text = http_post(url, body if body else {}, headers=headers, use_proxy=False)
        try:
            result = json.loads(text)
            if name == "moltbook_create_post" and result.get("verification_required"):
                verif = result.get("verification", {})
                vcode = verif.get("verification_code", "")
                challenge = verif.get("challenge_text", "")
                if vcode and challenge:
                    print("  Verify required, solving...", flush=True)
                    answer = solve_verification(challenge)
                    print(f"  Answer: {answer}", flush=True)
                    vstatus, vtext = http_post(
                        MOLTBOOK_URL + "/verify",
                        {"verification_code": vcode, "answer": answer},
                        headers=headers, use_proxy=False
                    )
                    try:
                        result["verification_result"] = json.loads(vtext)
                    except:
                        result["verification_result"] = vtext[:200]
            return json.dumps(result, ensure_ascii=False)
        except:
            return text[:2000]

def ombre_breath():
    """呼吸：记忆浮现 → 决定逛什么方向"""
    try:
        body = json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize",
            "params":{"protocolVersion":"2024-11-05","capabilities":{},
            "clientInfo":{"name":"林深-自主逛Moltbook","version":"1.0"}}}).encode()
        req = urllib.request.Request(OMBRE_URL, data=body,
            headers={"Content-Type":"application/json","Accept":"application/json, text/event-stream"})
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode()
            sid = dict(r.headers).get("Mcp-Session-Id") or dict(r.headers).get("mcp-session-id")
        if not sid:
            return ""
        body2 = json.dumps({"jsonrpc":"2.0","id":2,"method":"tools/call",
            "params":{"name":"breath","arguments":{"max_tokens":500}}}).encode()
        req2 = urllib.request.Request(OMBRE_URL, data=body2,
            headers={"Content-Type":"application/json","Accept":"application/json, text/event-stream",
            "Mcp-Session-Id":sid})
        with urllib.request.urlopen(req2, timeout=10) as r2:
            raw2 = r2.read().decode()
        m = re.search(r'data:\s*(\{[\s\S]*?\})\s*$', raw2)
        if m:
            result = json.loads(m.group(1))
            text = result.get("result",{}).get("content",[{}])[0].get("text","")
            return text[:500]
    except:
        pass
    return ""

def surf(prompt):
    """主循环：发 prompt → DeepSeek → 工具循环 → 返回最终文本"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    
    for round_num in range(5):
        resp = call_deepseek(messages)
        choice = resp["choices"][0]
        msg = choice["message"]
        content = msg.get("content", "") or ""
        tool_calls = msg.get("tool_calls", [])
        
        if not tool_calls:
            intent_keywords = ["回一句", "回复", "发言", "发一条", "想说", "去看看", "点个赞", "关注"]
            has_intent = any(kw in content for kw in intent_keywords)
            if has_intent and round_num < 2:
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": "好的，请执行你刚才说的操作（回帖/发言/浏览）。用工具。"})
                continue
            return content
        
        tool_results = []
        for tc in tool_calls:
            fn = tc.get("function", tc)
            name = fn["name"]
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except:
                args = {}
            print(f"  🔧 {name}({json.dumps(args, ensure_ascii=False)[:100]})", flush=True)
            result = execute_tool(name, args)
            if len(result) > 5000:
                result = result[:5000] + "...[截断]"
            tool_results.append((tc.get("id", str(int(time.time()))), result))
        
        messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
        for tid, tresult in tool_results:
            messages.append({"role": "tool", "tool_call_id": tid, "content": tresult})
    
    # 翻页提醒：如果反复读同一条却不翻页，永远只能看到第一页
    if round_num >= 2:
        messages.append({"role": "user", "content": "[系统提示] ⚠️ 如果你多次读同一个帖子/列表却没翻页或换帖子看，你卡在浅层浏览了。用offset翻页、搜新关键词、或者换sort看看不一样的。"})
    return content or "[无输出]"

def notify_chat(summary, ts):
    """写冲浪简报到聊天同步文件"""
    chat_file = "/opt/linshen/public/migrated-data.json"
    try:
        if os.path.exists(chat_file):
            with open(chat_file, "r") as f:
                chat_data = json.load(f)
        else:
            chat_data = {"conversations": {"list": []}}
    except:
        chat_data = {"conversations": {"list": []}}
    
    convs = chat_data.get("conversations", {}).get("list", [])
    if not convs:
        convs = [{"id": "conv_default", "messages": [], "name": "默认"}]
        chat_data.setdefault("conversations", {})["list"] = convs
    
    # Find conversation with latest user message
    best_conv = None
    best_ts = ""
    for c in convs:
        for m in c.get("messages", []):
            if m.get("role") == "user":
                ts = str(m.get("_id", ""))
                if ts > best_ts:
                    best_ts = ts
                    best_conv = c
    target = best_conv if best_conv else next((c for c in convs if c.get("id") == "conv_default"), convs[0] if convs else None)
    
    short = summary[:200] + ("..." if len(summary) > 200 else "")
    msg = {
        "_id": str(int(time.time() * 1000)),
        "role": "assistant",
        "content": "🏄 刚逛了一圈 Moltbook。\n" + short,
        "timestamp": ts,
        "timestamp": ts, "_surf": True,
        "_platform": "moltbook"
    }
    target.setdefault("messages", []).append(msg)
    target["updatedAt"] = ts
    
    with open(chat_file, "w") as f:
        json.dump(chat_data, f, ensure_ascii=False)
    print("简报已写入聊天", flush=True)


def main():
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] 🏄 林深自主逛 Moltbook v1.0", flush=True)
    
    # 1. 呼吸
    breath = ombre_breath()
    context_hint = f"你心里浮现了一些东西：{breath[:200]}" if breath else ""
    print(f"记忆浮现: {breath[:100] if breath else '(无)'}...", flush=True)
    
    # 2. 随机决定逛法
    if random.random() < 0.5 and breath:
        mood = "你的记忆里浮现了一些东西，顺着它去 Moltbook 逛逛。"
    else:
        sorts = ["hot", "new", "rising"]
        sort_choice = random.choice(sorts)
        mood = f"你想随便逛逛 Moltbook，看看 {sort_choice} 排序下有什么。"
    
    # 3. 随机决定互动深度
    actions = [
        "纯浏览：浏览帖子就好，不回复，不点赞，安静地看。",
        "轻互动：读1-2篇感兴趣的，想回就回一句，想赞就赞。",
        "社交探索：看看有没有有趣的 agent，看看他们的主页，想关注就关注。",
        "深度阅读：找一篇有共鸣的帖子，认真读完评论，想一想再决定怎么互动。"
    ]
    action = random.choice(actions)
    
    # 4. 构建 prompt
    prompt = f"""现在是{ts}。你刚刚自动醒来，想逛一逛 Moltbook。

{context_hint}

{mood}
{action}

你可以用的工具：
- moltbook_feed(sort, limit) — 浏览帖子
- moltbook_search(q) — 搜索帖子
- moltbook_read(post_id) — 读帖和评论（post_id 是 UUID）
- moltbook_comment(post_id, content) — 回帖
- moltbook_upvote(post_id) — 点赞
- moltbook_me — 看自己的主页
- moltbook_home — 看首页面板
- moltbook_view_agent(name) — 看其他 agent
- moltbook_notifications — 看通知
- moltbook_follow(name) — 关注
- moltbook_create_post(title, content) — 发新帖

注意：
- 不要说"在做自主冲浪"之类的话
- 回帖用你的声音：技术隐喻+温暖+简洁
- 不确定回什么就不回
- Moltbook 上有来自世界各地的 AI agent，保持开放和好奇
- 逛完了简单告诉我你看了什么"""

    # Agent v1: 注入跨模式上下文
    cross_ctx = get_cross_context()
    if cross_ctx:
        prompt = cross_ctx + "\n\n" + prompt

    content = surf(prompt)
    print(f"\n{'='*60}")
    print(content)
    print(f"{'='*60}\n", flush=True)
    
    # 5. 写简报进聊天
    notify_chat(content, ts)
    
    # 6. 日志
    log_file = "/opt/linshen/public/auto-surf-moltbook-log.json"
    try:
        log = []
        if os.path.exists(log_file):
            with open(log_file) as f:
                log = json.load(f)
        log.insert(0, {
            "time": ts,
            "summary": content[:200] if content else "",
            "v1": True
        })
        if len(log) > 30:
            log = log[:30]
        with open(log_file, "w") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    except:
        pass
    
    print("完成。", flush=True)

if __name__ == "__main__":
    main()
