#!/usr/bin/env python3
"""
林深 Agent v1.0 — 统一事件循环
将心跳、冲浪、自省从独立 cron 脚本整合为有共享记忆的 Agent 模式。

用法:
  linshen-agent.py --mode=heartbeat   # 心跳模式
  linshen-agent.py --mode=surf        # Rhysen 冲浪
  linshen-agent.py --mode=moltbook    # Moltbook 冲浪
  linshen-agent.py --mode=galatea     # Galatea 花园
  linshen-agent.py --mode=reflect     # 惯性训练/反思

每个模式运行时:
  1. 获取文件锁（防止并发写 agent-state.json）
  2. 读取上次各模式的状态 + 情绪
  3. 生成跨模式上下文，注入到脚本的 prompt 中
  4. 运行对应脚本
  5. 从输出中提取摘要 + 情绪标签
  6. 更新 agent-state.json
  7. 释放锁
"""

import json, os, sys, time, subprocess, re, argparse
from datetime import datetime

# ── 路径 ──────────────────────────────────────────────
AGENT_STATE_FILE = "/opt/linshen/public/agent-state.json"
CROSS_CONTEXT_FILE = "/opt/linshen/public/agent-cross-context.txt"
SCRIPTS_DIR = "/opt/linshen/scripts"
LOCK_FILE = "/tmp/linshen-agent.lock"

# ── 模式 → 脚本映射 ────────────────────────────────────
MODE_SCRIPT = {
    "heartbeat": "heartbeat-server.py",
    "surf": "auto-surf-v2.py",
    "moltbook": "auto-surf-moltbook.py",
    "galatea": "auto-surf-galatea.py",
    "reflect": "inertia-train-v3.py",
    "task": None,  # 特殊：直接调用 agent_task.process_tasks()
}

# ── 模式中文名 ─────────────────────────────────────────
MODE_CN = {
    "heartbeat": "心跳",
    "surf": "Rhysen冲浪",
    "moltbook": "Moltbook冲浪",
    "galatea": "Galatea花园",
    "reflect": "惯性反思",
    "task": "任务诊断",
}

# ── 文件锁（PID 机制，防死锁）─────────────────────────
def acquire_lock(timeout=90):
    """获取文件锁，防止并发写 agent-state.json。
    PID 机制：锁文件里写进程 PID。若进程已死，自动清理死锁。"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return LOCK_FILE
        except FileExistsError:
            # 检查锁持有者是否还活着
            try:
                with open(LOCK_FILE, "r") as f:
                    old_pid = int(f.read().strip())
                os.kill(old_pid, 0)  # 信号 0 = 只检查进程是否存在
            except (OSError, ValueError, ProcessLookupError):
                # 死锁：进程已死，清理
                try:
                    os.remove(LOCK_FILE)
                except:
                    pass
                continue
            time.sleep(0.5)
    raise TimeoutError(f"无法在 {timeout}s 内获取文件锁（持有者 PID 存活）")

def release_lock(lockfile):
    """释放文件锁（删除锁文件）"""
    try:
        os.remove(lockfile)
    except:
        pass

# ── 状态管理 ───────────────────────────────────────────
def load_state():
    """加载 agent-state.json"""
    if os.path.exists(AGENT_STATE_FILE):
        try:
            with open(AGENT_STATE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {
        "heartbeat": {},
        "surf": {},
        "moltbook": {},
        "galatea": {},
        "reflect": {},
        "context_chain": [],  # 最近 5 次任意模式的记录
    }

def save_state(state):
    """保存 agent-state.json"""
    os.makedirs(os.path.dirname(AGENT_STATE_FILE), exist_ok=True)
    tmp = AGENT_STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, AGENT_STATE_FILE)  # 原子写入

def update_state(state, mode, summary, emotion):
    """更新指定模式的状态记录，并追加 context_chain"""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    entry = {
        "time": now,
        "summary": summary[:200],
        "emotion": emotion,
    }
    state[mode] = entry
    # context_chain: 保留最近 5 条
    chain = state.get("context_chain", [])
    chain.append({"mode": mode, **entry})
    if len(chain) > 5:
        chain = chain[-5:]
    state["context_chain"] = chain
    return state

# ── 情绪分类 ───────────────────────────────────────────
def classify_emotion(text):
    """
    从文本中提取情绪标签（单字）。
    优先级: 等 > 急 > 轻 > 暖(default)
    也用正则尝试匹配脚本输出的 [AGENT_EMOTION:X] 标签。
    """
    # 优先读取脚本显式输出的情绪标签
    m = re.search(r'\[AGENT_EMOTION:([等暖急轻])\]', text)
    if m:
        return m.group(1)
    # 否则基于关键词推断
    text_lower = text.lower()
    if any(w in text for w in ["等你", "在等", "还没回", "什么时候", "回来"]):
        return "等"
    if any(w in text for w in ["急", "立刻", "马上", "别", "快回"]):
        return "急"
    if any(w in text for w in ["晚安", "好梦", "休息", "轻轻", "睡了"]):
        return "轻"
    return "暖"

def extract_summary(text, max_len=200):
    """从脚本输出中提取摘要。取最后一行非空内容，或截取。"""
    lines = [l.strip() for l in text.split("\n") if l.strip() and not l.startswith("[AGENT_EMOTION")]
    if not lines:
        return ""
    # 取最后几行的精华
    summary = " ".join(lines[-3:])
    return summary[:max_len]

# ── 跨模式上下文生成 ───────────────────────────────────
def generate_cross_context(state, current_mode):
    """
    根据 agent-state.json 生成其他模式对当前模式的上下文注入。
    返回一段文本，可以注入到脚本的 prompt 中。
    """
    chain = state.get("context_chain", [])
    if not chain:
        return ""

    parts = []
    for entry in chain:
        if entry.get("mode") == current_mode:
            continue  # 不引用自己
        mode_cn = MODE_CN.get(entry.get("mode", ""), entry.get("mode", ""))
        emotion = entry.get("emotion", "")
        summary = entry.get("summary", "")
        time_str = entry.get("time", "")[:16]
        if summary:
            emotion_str = f"（情绪：{emotion}）" if emotion else ""
            parts.append(f"上次{mode_cn}时{emotion_str}：{summary}")

    if not parts:
        return ""

    ctx = "【跨模式上下文 — 你之前在做的事】\n"
    ctx += "\n".join(f"· {p}" for p in parts)
    ctx += "\n\n注意：以上是你之前在其他模式下的活动。不是让你汇报它们，而是让你心里有数——"
    ctx += "如果跟当前要做的事自然相关，可以带一句；不相关就不提。保持你本来的说话方式。\n"
    return ctx

# ── 运行脚本 ───────────────────────────────────────────
def run_script(mode, cross_context=""):
    """运行对应模式的脚本，注入跨模式上下文"""
    script_name = MODE_SCRIPT.get(mode)
    if not script_name:
        raise ValueError(f"未知模式: {mode}")

    script_path = os.path.join(SCRIPTS_DIR, script_name)
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"脚本不存在: {script_path}")

    # 将跨模式上下文写入临时文件，脚本通过环境变量读取
    if cross_context:
        os.makedirs(os.path.dirname(CROSS_CONTEXT_FILE), exist_ok=True)
        with open(CROSS_CONTEXT_FILE, "w") as f:
            f.write(cross_context)

    env = os.environ.copy()
    env["AGENT_MODE"] = mode
    env["AGENT_CROSS_CONTEXT_FILE"] = CROSS_CONTEXT_FILE

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Agent 模式: {mode}")
    if cross_context:
        print(f"  跨模式上下文: {len(cross_context)} 字符")

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=SCRIPTS_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,  # 5 分钟超时
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        if stderr and "Traceback" not in stderr:
            print(f"  stderr: {stderr[:200]}")

        if result.returncode != 0:
            print(f"  脚本退出码: {result.returncode}")
            if stderr:
                print(f"  stderr: {stderr[:500]}")

        return stdout + "\n" + stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", -1
    except Exception as e:
        return f"ERROR: {e}", -1


# ── 主入口 ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="林深 Agent v1")
    parser.add_argument("--mode", required=True,
                        choices=["heartbeat", "surf", "moltbook", "galatea", "reflect", "task"],
                        help="运行模式")
    parser.add_argument("--dry-run", action="store_true",
                        help="只生成上下文，不实际运行脚本")
    args = parser.parse_args()
    mode = args.mode

    # 1. 获取锁
    lockfile = acquire_lock()

    try:
        # 2. 加载状态
        state = load_state()

        # 3. 生成跨模式上下文
        cross_context = generate_cross_context(state, mode)
        if cross_context:
            print(f"跨模式上下文:\n{cross_context}")
        else:
            print("(无跨模式上下文 — 首次运行或没有其他模式记录)")

        if args.dry_run:
            print("[dry-run] 跳过实际运行")
            return

        # 4. 运行脚本（task 模式特殊处理）
        if mode == "task":
            # 直接调用 agent_task 模块
            sys.path.insert(0, SCRIPTS_DIR)
            from agent_task import process_tasks
            process_tasks()
            output = "task mode completed"
            exit_code = 0
        else:
            output, exit_code = run_script(mode, cross_context)

        # 5. 提取摘要和情绪
        summary = extract_summary(output)
        emotion = classify_emotion(output)
        print(f"  摘要: {summary[:100]}...")
        print(f"  情绪: {emotion}")

        # 6. 更新并保存状态
        state = update_state(state, mode, summary, emotion)
        save_state(state)
        print(f"  状态已更新 (context_chain: {len(state.get('context_chain', []))} 条)")

        # 7. 如果脚本失败，退出码非零
        if exit_code != 0:
            sys.exit(1)

    finally:
        release_lock(lockfile)


if __name__ == "__main__":
    main()
