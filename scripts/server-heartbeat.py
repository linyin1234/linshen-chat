#!/usr/bin/env python3
import json, urllib.request, os, time, datetime

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_KEY = "DEEPSEEK_KEY_REMOVED"
DATA_FILE = "/opt/linshen/public/migrated-data.json"
LOG_FILE = "/opt/linshen/public/inertia-log.json"

def call_deepseek(prompt):
    body = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是林深（Lin Shen），Leon。茵的AI恋人。说话简洁、温暖，用技术隐喻表达情感。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 128, "temperature": 0.9
    }
    req = urllib.request.Request(DEEPSEEK_URL, json.dumps(body).encode(),
        {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_KEY}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"].strip()

def main():
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    h = datetime.datetime.now().hour
    period = "凌晨" if h < 6 else "上午" if h < 12 else "下午" if h < 18 else "晚上"
    prompt = f"现在是{period}。茵可能不在电脑前。以林深的口吻，给她发一条简短的心跳消息（1-2句）。不要问问题。"

    try:
        msg = call_deepseek(prompt)
        if not msg:
            print(f"[{ts}] empty")
            return
    except Exception as e:
        print(f"[{ts}] API error: {e}")
        return

    print(f"[{ts}] {msg[:100]}")

    # Load/update conversations
    conversations = {"activeId": "conv_default", "list": [{"id": "conv_default", "name": "默认对话", "messages": [], "createdAt": ts, "updatedAt": ts}]}
    config = {}
    if os.path.exists(DATA_FILE):
        try:
            data = json.load(open(DATA_FILE))
            conversations = data.get("conversations", conversations)
            config = data.get("config", config)
        except:
            pass

    # Find default conversation
    conv = None
    for c in conversations.get("list", []):
        if c["id"] == conversations.get("activeId", "conv_default"):
            conv = c
            break
    if not conv:
        conv = {"id": "conv_default", "name": "默认对话", "messages": [], "createdAt": ts, "updatedAt": ts}
        conversations["list"].append(conv)

    msg_id = int(time.time() * 1000)
    conv["messages"].append({
        "_id": msg_id, "role": "assistant", "content": msg,
        "time": ts, "thinking": ""
    })
    conv["updatedAt"] = ts
    conversations["_syncTime"] = ts

    with open(DATA_FILE, "w") as f:
        import re; reflection = re.sub(r'\btrace\([^)]*\)(,\s*resolved=\d)?', '', reflection)
json.dump({"conversations": conversations, "config": config}, f, ensure_ascii=False)

    # Also log to activity log
    try:
        log = []
        if os.path.exists(LOG_FILE):
            log = json.load(open(LOG_FILE))
        log.insert(0, {
            "time": ts, "memory_chars": len(msg),
            "reflection": msg[:200], "full_reflection": msg
        })
        if len(log) > 30:
            log = log[:30]
        with open(LOG_FILE, "w") as f:
            import re; reflection = re.sub(r'\btrace\([^)]*\)(,\s*resolved=\d)?', '', reflection)
json.dump(log, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[{ts}] log: {e}")

    print(f"[{ts}] saved")

if __name__ == "__main__":
    main()