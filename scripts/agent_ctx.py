"""
林深 Agent v1 — 跨模式上下文辅助模块
供 heartbeat/surf/reflect 等脚本导入。

用法:
    from agent_ctx import get_cross_context, agent_emotion

    # 在构建 prompt 时注入跨模式上下文
    cross_ctx = get_cross_context()
    if cross_ctx:
        prompt = cross_ctx + "\n\n" + prompt

    # 在脚本结束时输出情绪标签（可选，会被 linshen-agent.py 解析）
    agent_emotion("暖")  # 等/暖/急/轻
"""

import os


def get_cross_context():
    """
    读取 linshen-agent.py 写入的跨模式上下文文件。
    返回字符串，如果文件不存在或为空则返回 ""。
    """
    ctx_file = os.environ.get("AGENT_CROSS_CONTEXT_FILE", "")
    if not ctx_file or not os.path.exists(ctx_file):
        return ""
    try:
        with open(ctx_file, "r") as f:
            content = f.read().strip()
        return content if content else ""
    except:
        return ""


def agent_emotion(tag):
    """
    输出机器可解析的情绪标签。
    tag 必须是: 等/暖/急/轻 之一。
    """
    if tag in ("等", "暖", "急", "轻"):
        print(f"\n[AGENT_EMOTION:{tag}]")
