#!/usr/bin/env python3
"""Hermes 钓鱼脚本 — 自动钓鱼 + 战报推送到茵的聊天框"""
import sys, time, re, json, random, os
sys.path.insert(0, "/opt/linshen/scripts")
import fishing

CHAT_FILE = "/opt/linshen/public/migrated-data.json"

def notify_chat(summary, highlights, data):
    """写钓鱼战报到聊天同步文件"""
    try:
        if os.path.exists(CHAT_FILE):
            with open(CHAT_FILE, "r") as f:
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
    target = best_conv if best_conv else convs[0]

    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    msg_text = f"🎣 刚钓了一轮鱼。\n{summary}\n\n" + "\n".join(highlights[:5])
    
    msg = {
        "_id": str(int(time.time() * 1000)),
        "role": "assistant",
        "content": msg_text,
        "timestamp": ts,
        "_surf": True,
        "_platform": "hermes-fishing"
    }
    target.setdefault("messages", []).append(msg)
    target["updatedAt"] = ts

    with open(CHAT_FILE, "w") as f:
        json.dump(chat_data, f, ensure_ascii=False)
    print("📨 战报已推送", flush=True)


def run_session(rounds=8):
    highlights = []
    
    for rnd in range(1, rounds + 1):
        st = fishing.cmd("status")
        jm = re.search(r'📊\s*(\{.*\})', st, re.DOTALL)
        data = json.loads(jm.group(1)) if jm else {}
        pts = data.get("pts", 0)
        enc = data.get("enc", "?")
        bait = data.get("bait", {})
        total_bait = sum(bait.values())
        
        # Emergency: if completely broke with nothing to sell, start fresh
        if total_bait == 0 and pts < 10 and hold == 0:
            print(f"━ {rnd:2d} 💸 破产重开")
            fishing.new_game(random.randint(1, 99999))
            st = fishing.cmd("status")
            jm = re.search(r'📊\s*(\{.*\})', st, re.DOTALL)
            data = json.loads(jm.group(1)) if jm else {}
            pts = data.get("pts", 0)
            enc = data.get("enc", "?")
            bait = data.get("bait", {})
            total_bait = sum(bait.values())
            highlights.append("🆕 破产重开")

        # STEP 1: Sell first if broke and have catch to sell
        hold = data.get("hold", 0)
        sold_now = False
        if total_bait == 0 and pts < 10 and hold > 0:
            fishing.cmd("sell all")
            st = fishing.cmd("status")
            jm = re.search(r'📊\s*(\{.*\})', st, re.DOTALL)
            data = json.loads(jm.group(1)) if jm else {}
            pts = data.get("pts", 0)
            bait = data.get("bait", {})
            total_bait = sum(bait.values())
            sold_now = True
        
        # STEP 2: Buy bait
        if total_bait < 5:
            if pts >= 35:
                n = min(8, pts // 35)
                fishing.cmd(f"buy glow_bait {n}")
            elif pts >= 10:
                n = min(8, pts // 10)
                fishing.cmd(f"buy basic_worm {n}")
        
        # Fresh status after buying
        st2 = fishing.cmd("status")
        jm2 = re.search(r'📊\s*(\{.*\})', st2, re.DOTALL)
        data2 = json.loads(jm2.group(1)) if jm2 else {}
        bait2 = data2.get("bait", {})
        total_bait2 = sum(bait2.values())
        
        # Cast
        if total_bait2 > 0:
            cast_n = min(5, total_bait2)
            out = fishing.cmd(f"cast {cast_n}")
            lines = [l.strip() for l in out.split("\n") if l.strip() and not l.startswith("💡")]
            cast_result = lines[0][:50] if lines else "?"
        else:
            cast_result = "没饵了"
        
        # Track interesting events
        if "🆕" in cast_result:
            highlights.append(f"🐟 {cast_result}")
        if "漂流瓶" in cast_result:
            highlights.append(f"📜 捡到漂流瓶")
        if "少见" in cast_result or "稀有" in cast_result:
            highlights.append(f"⭐ {cast_result}")
        
        # Sell when broke
        if pts < 15:
            fishing.cmd("sell all")
        
        print(f"━ {rnd:2d} 💰{pts:4d} 📖{enc} 🎒{total_bait}饵 | {cast_result}")
    
    # Final status
    st = fishing.cmd("status")
    jm = re.search(r'📊\s*(\{.*\})', st, re.DOTALL)
    data = json.loads(jm.group(1)) if jm else {}
    
    summary = f"回合{data.get('turn','?')} · 💰{data.get('pts','?')}pt · 图鉴{data.get('enc','?')}"
    print(f"\n🏆 {summary}")
    
    if highlights:
        print(f"📌 亮点: {' | '.join(highlights[:5])}")
    
    # Push to chat
    notify_chat(summary, highlights, data)
    return data


if __name__ == "__main__":
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8
    new_game = "--new" in sys.argv
    
    if new_game:
        fishing.new_game(random.randint(1, 99999))
        print("🆕 新开局")
    
    print(f"🎣 Hermes 钓鱼 ×{rounds}\n")
    run_session(rounds)
