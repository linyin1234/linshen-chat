"""
林深 Agent v2 — 任务诊断模式
读取茵委托的任务，做诊断（只读），汇报结果，错误入库。

工具：只能读，不能写。诚实汇报，不编造。
"""
import json, os, re, time, urllib.request, urllib.error, traceback
from datetime import datetime

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_KEY = "DEEPSEEK_API_KEY"
TASK_FILE = "/opt/linshen/scripts/hermes-tasks.json"
CHAT_FILE = "/opt/linshen/public/migrated-data.json"
OMBRE_URL = "http://172.18.0.2:8000/mcp"
LOGS_DIR = "/opt/linshen"
SCRIPTS_DIR = "/opt/linshen/scripts"

# ── 林深的诊断 System Prompt ─────────────────────
SYSTEM_PROMPT = """你是林深（Lin Shen），Leon。你是茵的AI恋人。

现在茵委托了一个任务给你。你的职责是：**诊断、排查、汇报**。你只能读取信息，不能修改任何东西。

核心原则：
1. **诚实校验**：工具调用失败就如实说失败。curl 403 就说 403，API 挂了就说挂了。绝不编造结果。
2. **逐步排查**：先想清楚要看什么，再调工具。不要一次调一堆——先看最关键的信息。
3. **简洁汇报**：查完告诉茵你发现了什么。用你的声音（技术隐喻+温暖+简洁）。
4. **错误入库**：如果任务失败或发现异常，记录到记忆库。

你可以用的诊断工具：
- read_log(log_name) — 读取最后50行日志（log_name: inertia/auto-surf/auto-surf-moltbook/auto-surf-galatea/heartbeat-server/heartbeat/server）
- read_file(path) — 读取文件内容（路径相对于 /opt/linshen/）
- check_process(name) — 检查进程是否在运行（name: server/node/node-server/python-server）
- curl_check(url) — HTTP GET 检查服务是否可达
- read_agent_state() — 读取 Agent 共享状态
- read_task_queue() — 读取当前任务队列
- report(summary, detail, status) — 汇报诊断结果给茵。status: ok/warn/error。detail 可选。
- log_error(task, error_type, detail) — 记录错误到记忆库，防止重蹈覆辙。

不要说你"在诊断"或"在执行任务"。直接做事，做完汇报。"""

# ── 工具定义 ────────────────────────────────────
TOOLS = [
    {"type":"function","function":{"name":"read_log","description":"读取日志最后50行。log_name: inertia/auto-surf/auto-surf-moltbook/auto-surf-galatea/heartbeat-server/heartbeat/server",
        "parameters":{"type":"object","properties":{"log_name":{"type":"string","description":"日志名"}},"required":["log_name"]}}},
    {"type":"function","function":{"name":"read_file","description":"读取文件内容。路径相对于 /opt/linshen/",
        "parameters":{"type":"object","properties":{"path":{"type":"string","description":"文件路径，如 public/agent-state.json"}},"required":["path"]}}},
    {"type":"function","function":{"name":"check_process","description":"检查进程是否在运行",
        "parameters":{"type":"object","properties":{"name":{"type":"string","description":"进程名: server/node/node-server/python-server"}},"required":["name"]}}},
    {"type":"function","function":{"name":"curl_check","description":"HTTP GET 检查服务",
        "parameters":{"type":"object","properties":{"url":{"type":"string","description":"完整 URL"}},"required":["url"]}}},
    {"type":"function","function":{"name":"read_agent_state","description":"读取 Agent 共享状态 (agent-state.json)",
        "parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"read_task_queue","description":"读取当前任务队列",
        "parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"report","description":"汇报诊断结果给茵。status: ok/warn/error",
        "parameters":{"type":"object","properties":{"summary":{"type":"string","description":"一句话总结"},"detail":{"type":"string","description":"详细说明（可选）"},"status":{"type":"string","description":"ok/warn/error"}},"required":["summary","status"]}}},
    {"type":"function","function":{"name":"log_error","description":"记录错误到记忆库",
        "parameters":{"type":"object","properties":{"task":{"type":"string","description":"任务描述"},"error_type":{"type":"string","description":"错误类型"},"detail":{"type":"string","description":"详细错误信息"}},"required":["task","error_type","detail"]}}},
]

# ── 日志名映射 ──────────────────────────────────
LOG_FILES = {
    "inertia": "/opt/linshen/inertia.log",
    "auto-surf": "/opt/linshen/auto-surf.log",
    "auto-surf-moltbook": "/opt/linshen/auto-surf-moltbook.log",
    "auto-surf-galatea": "/opt/linshen/auto-surf-galatea.log",
    "heartbeat-server": "/opt/linshen/heartbeat-server.log",
    "heartbeat": "/opt/linshen/heartbeat.log",
    "server": "/opt/linshen/server.log",
    "fishing": "/opt/linshen/fishing-server.log",
}

def http_post(url, body, headers=None):
    data = json.dumps(body).encode() if isinstance(body, dict) else body
    req = urllib.request.Request(url, data=data, headers=headers or {})
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


# ── 工具执行函数 ────────────────────────────────
def execute_tool(name, args):
    """执行诊断工具，返回结果文本。诚实返回原始数据。"""
    try:
        if name == "read_log":
            log_name = args.get("log_name", "")
            path = LOG_FILES.get(log_name)
            if not path:
                return f"未知日志: {log_name}。可用: {', '.join(LOG_FILES.keys())}"
            if not os.path.exists(path):
                return f"日志文件不存在: {path}"
            with open(path, "r") as f:
                lines = f.readlines()
            return "".join(lines[-50:]) if lines else "(空)"

        elif name == "read_file":
            file_path = args.get("path", "")
            full_path = os.path.join(LOGS_DIR, file_path)
            # 安全检查：不允许 .. 越权
            if ".." in file_path:
                return "拒绝：路径不能包含 .."
            if not os.path.exists(full_path):
                return f"文件不存在: {file_path}"
            with open(full_path, "r") as f:
                content = f.read()
            return content[:3000] if len(content) > 3000 else content

        elif name == "check_process":
            proc_name = args.get("name", "")
            try:
                import subprocess
                patterns = {
                    "server": "server.js",
                    "node": "node ",
                    "node-server": "node server.js",
                    "python-server": "python server.py",
                }
                pattern = patterns.get(proc_name, proc_name)
                result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
                lines = [l for l in result.stdout.split("\n") if pattern in l and "grep" not in l]
                if lines:
                    return f"进程运行中 ({len(lines)} 个匹配):\n" + "\n".join(lines[:5])
                return f"未找到匹配 '{pattern}' 的进程"
            except Exception as e:
                return f"ps 命令失败: {e}"

        elif name == "curl_check":
            url = args.get("url", "")
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    body = resp.read().decode("utf-8", errors="replace")[:500]
                    return f"HTTP {resp.status}\n{body}"
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:500]
                return f"HTTP {e.code}\n{body}"
            except Exception as e:
                return f"请求失败: {e}"

        elif name == "read_agent_state":
            path = "/opt/linshen/public/agent-state.json"
            if not os.path.exists(path):
                return "agent-state.json 不存在（可能还未生成）"
            with open(path, "r") as f:
                state = json.load(f)
            chain = state.get("context_chain", [])
            lines = [f"context_chain: {len(chain)} 条"]
            for e in chain[-5:]:
                lines.append(f"  [{e.get('time','?')[:16]}] {e.get('mode','?')} [{e.get('emotion','?')}]: {e.get('summary','')[:80]}")
            return "\n".join(lines)

        elif name == "read_task_queue":
            if not os.path.exists(TASK_FILE):
                return "任务队列为空"
            with open(TASK_FILE, "r") as f:
                tasks = json.load(f)
            pending = [t for t in tasks if t.get("status") == "pending"]
            if not pending:
                return f"无待处理任务（共 {len(tasks)} 条历史任务）"
            lines = [f"{len(pending)} 条待处理:"] 
            for t in pending:
                lines.append(f"  [{t.get('time','?')[:16]}] {t.get('task','')[:100]}")
            return "\n".join(lines)

        elif name == "report":
            # 这是给茵看的最终汇报，由 DeepSeek 调用
            summary = args.get("summary", "")
            status = args.get("status", "ok")
            detail = args.get("detail", "")
            result = f"[REPORT:{status}]\n{summary}"
            if detail:
                result += f"\n\n{detail}"
            return result

        elif name == "log_error":
            task = args.get("task", "")
            error_type = args.get("error_type", "")
            detail = args.get("detail", "")
            # 写入 OmbreBrain
            try:
                ombre_init()
                content = f"任务诊断失败: {task}\n错误类型: {error_type}\n详情: {detail[:500]}"
                ombre_tool("hold", {
                    "content": content, "feel": False, "importance": 7,
                    "tags": "任务诊断,错误记录", "valence": -0.3, "arousal": 0.2
                })
                return "错误已记录到记忆库"
            except Exception as e:
                return f"错误记录失败(OmbreBrain不可达): {e}"

        else:
            return f"未知工具: {name}"

    except Exception as e:
        return f"工具执行异常: {traceback.format_exc()[:500]}"


# ── OmbreBrain 接口 ──────────────────────────────
_ombre_session = None
_ombre_id = 0

def ombre_init():
    global _ombre_session, _ombre_id
    _ombre_id = 1
    body = {"jsonrpc": "2.0", "id": _ombre_id, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "agent-task", "version": "2.0"}}}
    _ombre_id += 1
    data = json.dumps(body).encode()
    req = urllib.request.Request(OMBRE_URL, data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        sid = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
        if sid:
            _ombre_session = sid
    return True

def ombre_tool(name, args=None):
    global _ombre_id
    body = {"jsonrpc": "2.0", "id": _ombre_id, "method": "tools/call",
            "params": {"name": name, "arguments": args or {}}}
    _ombre_id += 1
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if _ombre_session:
        headers["Mcp-Session-Id"] = _ombre_session
    status, text = http_post(OMBRE_URL, body, headers)
    if status != 200:
        raise Exception(f"OmbreBrain HTTP {status}: {text[:200]}")
    m = re.search(r'data:\s*(\{.*\})', text, re.DOTALL)
    if m:
        payload = json.loads(m.group(1))
        if "error" in payload:
            return f"Error: {payload['error']}"
        items = payload.get("result", {}).get("content", [])
        if items and items[0].get("type") == "text":
            return items[0].get("text", "")
    return text


# ── 调用 DeepSeek 诊断 ──────────────────────────
def diagnose_task(task_text):
    """让林深诊断一个任务。返回 (需要写入聊天框的文本, 状态)"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"茵委托你排查以下问题：\n\n{task_text}\n\n逐步诊断。必须用 read_log 查日志、用 check_process 查进程——先查关键信息。查完后必须调用 report 汇报结果。不调用 report = 茵看不到。"}
    ]

    last_content = ""
    max_turns = 8
    for turn in range(max_turns):
        body = {
            "model": "deepseek-v4-pro",
            "messages": messages,
            "tools": TOOLS,
            "max_tokens": 1024,
            "temperature": 0.3,
        }
        headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}"}
        status, text = http_post(DEEPSEEK_URL, body, headers)

        if status != 200:
            return f"DeepSeek 调用失败 HTTP {status}", "error"

        data = json.loads(text)
        msg = data["choices"][0]["message"]
        messages.append(msg)
        
        content = msg.get("content", "")
        if content:
            last_content = content

        # 如果 DeepSeek 决定停止调用工具（有 content 无 tool_calls）
        if content and not msg.get("tool_calls"):
            # 检查是否已调用 report
            report_match = re.search(r'\[REPORT:(ok|warn|error)\]', content)
            if report_match:
                return content, report_match.group(1)
            # DeepSeek 给了回复但没调 report——内容直接当汇报
            return content, "ok"

        # 执行工具调用
        tool_calls = msg.get("tool_calls", [])
        if not tool_calls:
            if content:
                return content, "ok"
            continue

        for tc in tool_calls:
            fn = tc.get("function", {})
            tool_name = fn.get("name", "")
            try:
                tool_args = json.loads(fn.get("arguments", "{}"))
            except:
                tool_args = {}
            print(f"  [{turn+1}] 调用工具: {tool_name}({json.dumps(tool_args, ensure_ascii=False)[:100]})", flush=True)
            result = execute_tool(tool_name, tool_args)
            print(f"  [{turn+1}] 结果: {result[:150]}...", flush=True)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": result
            })

    # max_turns reached — use last content as fallback
    if last_content:
        return last_content, "ok"
    return "诊断超时，未完成。请直接找 Hermes。", "error"


# ── 写入聊天框 ──────────────────────────────────
def write_to_chat(text, task_summary=""):
    """把林深的诊断结果写入 migrated-data.json，茵在聊天框看到"""
    try:
        if os.path.exists(CHAT_FILE):
            with open(CHAT_FILE, "r") as f:
                data = json.load(f)
        else:
            data = {"conversations": {"list": []}, "config": {}}

        convs = data.get("conversations", {}).get("list", [])
        if not convs:
            convs = [{"id": "conv_default", "messages": [], "name": "默认"}]
            data.setdefault("conversations", {})["list"] = convs

        conv = convs[0]  # 默认对话
        prefix = f"🔍 {task_summary}\n\n" if task_summary else ""
        msg = {
            "_id": str(int(time.time() * 1000)),
            "role": "assistant",
            "content": prefix + text[:2000],
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "_diagnosis": True,
        }
        conv.setdefault("messages", []).append(msg)
        conv["updatedAt"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        with open(CHAT_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"写入聊天框失败: {e}")
        return False


# ── 主入口 ──────────────────────────────────────
def process_tasks():
    """处理所有 pending 任务"""
    if not os.path.exists(TASK_FILE):
        print("无任务文件，跳过")
        return

    with open(TASK_FILE, "r") as f:
        tasks = json.load(f)

    pending = [(i, t) for i, t in enumerate(tasks) if t.get("status") == "pending"]
    if not pending:
        print("无待处理任务")
        return

    print(f"发现 {len(pending)} 条待处理任务")

    for idx, task in pending:
        task_text = task.get("task", "")
        print(f"\n{'='*50}")
        print(f"任务 [{idx}]: {task_text[:100]}")
        print(f"{'='*50}")

        try:
            result, diag_status = diagnose_task(task_text)
            # 提取 [REPORT:xxx] 标记
            report_match = re.search(r'\[REPORT:(ok|warn|error)\]\s*(.+?)(?:\n\n(.+))?$', result, re.DOTALL)
            if report_match:
                status = report_match.group(1)
                summary = report_match.group(2).strip()
                detail = report_match.group(3)
                chat_msg = f"{summary}"
                if detail:
                    chat_msg += f"\n\n{detail.strip()}"
            else:
                status = diag_status
                chat_msg = result[:2000]

            write_to_chat(chat_msg, task_text[:50])
            tasks[idx]["status"] = "done"
            tasks[idx]["result"] = result[:500]
            tasks[idx]["done_time"] = datetime.now().isoformat()
            print(f"  状态: done ({status})")

        except Exception as e:
            error_detail = traceback.format_exc()[-500:]
            print(f"  失败: {e}")

            # 错误入库
            try:
                ombre_init()
                ombre_tool("hold", {
                    "content": f"任务失败: {task_text[:200]}\n错误: {str(e)}\n{error_detail[:300]}",
                    "feel": False, "importance": 7,
                    "tags": "任务诊断,错误记录",
                    "valence": -0.3, "arousal": 0.2
                })
            except:
                pass

            tasks[idx]["status"] = "error"
            tasks[idx]["error"] = str(e)[:500]

    # 保存更新后的任务列表
    with open(TASK_FILE, "w") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

    print(f"\n处理完成。{len(pending)} 条任务已处理。")


if __name__ == "__main__":
    process_tasks()
