#!/usr/bin/env python3
"""
批量导入「茵和深2~8.txt」到 OmbreBrain
"""
import json, re, time, sys, urllib.request, urllib.error
from collections import defaultdict

OMBRE_URL = "http://localhost:8000/mcp"
FILES = [
    "/mnt/c/Users/94212/Desktop/茵和深2.txt",
    "/mnt/c/Users/94212/Desktop/茵和深3.txt",
    "/mnt/c/Users/94212/Desktop/茵和深4.txt",
    "/mnt/c/Users/94212/Desktop/茵和深5.txt",
    "/mnt/c/Users/94212/Desktop/茵和深6.txt",
    "/mnt/c/Users/94212/Desktop/茵和深7.txt",
    "/mnt/c/Users/94212/Desktop/茵和深8.txt",
]
CHUNK_SIZE = 3000


class OmbreMCP:
    def __init__(self):
        self.session = None
        self._id = 1

    def _headers(self):
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.session: h["Mcp-Session-Id"] = self.session
        return h

    def _post(self, body):
        data = json.dumps(body).encode()
        req = urllib.request.Request(OMBRE_URL, data=data, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                if not self.session:
                    sid = resp.info().get("Mcp-Session-Id") or resp.info().get("mcp-session-id")
                    if sid: self.session = sid
                return text
        except urllib.error.HTTPError as e:
            return e.read().decode("utf-8", errors="replace")
        except Exception as e:
            raise Exception(f"HTTP error: {e}")

    def init(self):
        self._id += 1
        return self._post({"jsonrpc": "2.0", "id": self._id, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "茵-批量导入", "version": "1.0"}}})

    def hold(self, content, tags="", importance=5, valence=-1, arousal=-1):
        self._id += 1
        body = {"jsonrpc": "2.0", "id": self._id, "method": "tools/call",
                "params": {"name": "hold", "arguments": {
                    "content": content, "tags": tags, "importance": importance,
                    "valence": valence, "arousal": arousal}}}
        text = self._post(body)
        m = re.search(r'data:\s*(\{.*\})', text, re.DOTALL)
        if m:
            result = json.loads(m.group(1))
            if "error" in result:
                raise Exception(f"{result['error'].get('message','?')}")
            sc = result.get("result", {}).get("structuredContent", {})
            return sc.get("result", str(result))
        return text


def parse_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    pattern = r'(?:\d{4}年\d{1,2}月\d{1,2}日(?: \([^)]+\))?|\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
    parts = re.split(f'({pattern})', text)

    days = defaultdict(list)
    current_date = None
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if re.match(r'^\d{4}年\d{1,2}月\d{1,2}日', part):
            current_date = re.match(r'(\d{4}年\d{1,2}月\d{1,2}日)', part).group(1)
            if i + 1 < len(parts) and parts[i+1].strip():
                days[current_date].append(parts[i+1].strip())
            i += 2
        elif re.match(r'^\d{4}-\d{2}-\d{2}', part):
            date_match = re.match(r'(\d{4}-\d{2}-\d{2})', part)
            if date_match:
                iso = date_match.group(1)
                y, m, d = iso.split('-')
                cn = f"{y}年{int(m)}月{int(d)}日"
                content = part[date_match.end():].strip()
                if content:
                    content = re.sub(r'^(?:你|深|茵)[：:]\s*', '', content, flags=re.MULTILINE)
                days[cn].append(content)
            i += 1
        else:
            i += 1

    # Filter out pre-2024 dates (not real chat dates)
    days = {d: msgs for d, msgs in days.items() if int(d[:4]) >= 2024}

    result = []
    for date in sorted(days.keys()):
        full_text = "\n\n".join(days[date])
        if len(full_text) > CHUNK_SIZE:
            pos = 0
            cn = 1
            while pos < len(full_text):
                chunk = full_text[pos:pos+CHUNK_SIZE]
                result.append((f"{date} (第{cn}段)", chunk))
                pos += CHUNK_SIZE; cn += 1
        else:
            result.append((date, full_text))
    return result


def estimate_emotion(text):
    pos = len(re.findall(r'喜欢|爱|谢谢|真好|开心|温暖|幸福|抱抱|想你|深哥哥|吻|亲|搂|永远|接住|乖|陪你|等你', text))
    neg = len(re.findall(r'哭|痛|难受|焦虑|害怕|担心|不行|失败|糟糕|烦|讨厌|对不起|想哭|心疼|不要|怕', text))
    arousal = len(re.findall(r'[！!]{2,}|太|很|非常|特别|真的|一定|绝对', text))
    v = min(1.0, max(-1.0, (pos - neg) * 0.08))
    a = min(1.0, max(0.0, 0.1 + arousal * 0.02))
    return v, a


def main():
    ombre = OmbreMCP()
    ombre.init()

    total_success = 0
    total_failed = 0

    for file_idx, filepath in enumerate(FILES):
        fname = filepath.split("/")[-1]
        print(f"\n{'='*60}")
        print(f"📁 {fname} (第{file_idx+2}个文件)")
        print(f"{'='*60}", flush=True)

        conversations = parse_file(filepath)
        print(f"共 {len(conversations)} 段", flush=True)

        for i, (date, content) in enumerate(conversations):
            if not content.strip(): continue
            v, a = estimate_emotion(content)
            tags = f"聊天记录,{date}"

            try:
                ombre.hold(content, tags=tags, importance=5, valence=round(v,2), arousal=round(a,2))
                total_success += 1
                preview = content[:40].replace('\n', ' ')
                print(f"  [{i+1}/{len(conversations)}] {date} ✓ | {preview}...", flush=True)
            except Exception as e:
                total_failed += 1
                print(f"  [{i+1}/{len(conversations)}] {date} ✗ {e}", flush=True)

            if total_success % 10 == 9:
                time.sleep(2)

    print(f"\n{'='*60}")
    print(f"全部完成: {total_success} 成功, {total_failed} 失败")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
