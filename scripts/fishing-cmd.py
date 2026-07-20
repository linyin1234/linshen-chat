#!/usr/bin/env python3
"""Fishing game command wrapper — supports auto-session mode for Lin Shen."""
import sys, os, re, json, random

sys.path.insert(0, '/opt/linshen/scripts')
import fishing

cmd = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'status'

# ── Auto session mode ──
if cmd.startswith('auto'):
    parts = cmd.split()
    max_rounds = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 8
    
    if 'new' in cmd:
        fishing.new_game(random.randint(1, 99999))
    
    output = [f"🎣 自动钓鱼 ×{max_rounds}\n"]
    skip_count = 0
    
    for rnd in range(1, max_rounds + 1):
        st = fishing.cmd("status")
        jm = re.search(r'📊\s*(\{.*\})', st, re.DOTALL)
        data = json.loads(jm.group(1)) if jm else {}
        pts = data.get("pts", 0)
        enc = data.get("enc", "?")
        bait = data.get("bait", {})
        total_bait = sum(bait.values())
        hold = data.get("hold", 0)
        
        # STEP 1: Sell first if we have catch AND can't afford bait
        if total_bait == 0 and pts < 10 and hold > 0:
            fishing.cmd("sell all")
            st = fishing.cmd("status")
            jm = re.search(r'📊\s*(\{.*\})', st, re.DOTALL)
            data = json.loads(jm.group(1)) if jm else {}
            pts = data.get("pts", 0)
            bait = data.get("bait", {})
            total_bait = sum(bait.values())
            sold_msg = " 💵卖鱼补饵"
        else:
            sold_msg = ""
        
        # STEP 2: Buy bait if low
        if total_bait < 5:
            if pts >= 35:
                n = min(8, pts // 35)
                fishing.cmd(f"buy glow_bait {n}")
            elif pts >= 10:
                n = min(8, pts // 10)
                fishing.cmd(f"buy basic_worm {n}")
        
        # Refresh bait count after buying
        st2 = fishing.cmd("status")
        jm2 = re.search(r'📊\s*(\{.*\})', st2, re.DOTALL)
        data2 = json.loads(jm2.group(1)) if jm2 else {}
        bait2 = data2.get("bait", {})
        total_bait2 = sum(bait2.values())
        
        # STEP 3: Cast
        if total_bait2 > 0:
            cast_n = min(5, total_bait2)
            out = fishing.cmd(f"cast {cast_n}")
            lines = [l.strip() for l in out.split("\n") if l.strip() and not l.startswith("💡") and not l.startswith("📊")]
            cast_result = lines[0][:50] if lines else "?"
        else:
            cast_result = "没饵了"
            skip_count += 1
            if skip_count >= 3:
                output.append(f"第{rnd}轮 💰{pts} 📖{enc} | ⚠️ 连空{skip_count}轮，无饵无点，提前结束")
                break
        
        # STEP 4: Periodic sell to keep cash flowing
        if rnd % 3 == 0:
            fishing.cmd("sell all")
            if not sold_msg:
                sold_msg = " 💵卖鱼"
        
        output.append(f"第{rnd}轮 💰{pts} 📖{enc} | {cast_result}{sold_msg}")
    
    # Final
    st = fishing.cmd("status")
    jm = re.search(r'📊\s*(\{.*\})', st, re.DOTALL)
    data = json.loads(jm.group(1)) if jm else {}
    
    summary = st.split("\n")[0]
    output.append(f"\n📊 {summary}")
    output.append(f"回合{data.get('turn','?')} | 💰{data.get('pts','?')}pt | 图鉴{data.get('enc','?')}")
    
    print("\n".join(output))

# ── Normal command mode ──
else:
    print(fishing.cmd(cmd))
