#!/usr/bin/env python3
"""Hermes's auto-fishing script — plays the fishing game optimally."""

import urllib.request
import json
import time
import ssl
import random

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fish(cmd):
    url = f"https://47.237.92.158/api/fishing?cmd={urllib.request.quote(cmd)}"
    resp = urllib.request.urlopen(url, timeout=10, context=ctx)
    return resp.read().decode()

def parse_status(output):
    """Extract pts, location, season, bait dict from status output."""
    try:
        j = json.loads(output.split("📊")[-1].strip())
        return j
    except:
        return {}

def run():
    print("🎣 Hermes 自动钓鱼开始\n")
    
    for round_num in range(1, 11):
        time.sleep(0.5)
        
        # Check state
        raw = fish("status")
        st = parse_status(raw)
        pts = st.get("pts", 0)
        bait = st.get("bait", {})
        total_bait = sum(bait.values())
        held = st.get("hold", 0)
        enc = st.get("enc", "?/81")
        
        print(f"━━━ 第{round_num}轮 ━━━")
        print(f"  💰 {pts}pts | 🎒 {total_bait}饵 | 🐟 持{held}条 | 📖 {enc}")
        
        # Decision: buy bait if low
        if total_bait < 3 and pts >= 140:
            n = min(5, pts // 35)
            if n > 0:
                raw = fish(f"buy glow_bait {n}")
                st2 = parse_status(raw)
                pts = st2.get("pts", pts)
                print(f"  🛒 补夜光饵×{n} → {pts}pts")
        
        # Sell if holding 3+
        if held >= 3:
            raw = fish("sell all")
            st2 = parse_status(raw)
            pts = st2.get("pts", pts)
            print(f"  💵 卖鱼 → {pts}pts")
        
        # Decide how to fish
        glow = bait.get("glow_bait", 0)
        basic = bait.get("basic_worm", 0)
        golden = bait.get("golden_lure", 0)
        
        if glow > 0:
            n = min(glow, 5)
            cmd = f"cast glow_bait {n} stop=rare,new"
        elif basic > 0:
            n = min(basic, 5)
            cmd = f"cast basic_worm {n} stop=rare,new"
        elif golden > 0:
            cmd = "cast golden_lure 1 stop=rare"
        elif pts >= 35:
            # No bait, buy and continue
            raw = fish("buy glow_bait 1")
            st2 = parse_status(raw)
            pts = st2.get("pts", pts)
            cmd = "cast glow_bait 1"
        else:
            print("  💤 没钱没饵，停")
            break
        
        raw = fish(cmd)
        # Extract interesting events
        for line in raw.split('\n'):
            if any(kw in line for kw in ['🆕', '🌟', '🗺️', '📜', '🌊', '🍃', '🪝']):
                print(f"  {line.strip()}")
        
        st2 = parse_status(raw)
        new_enc = st2.get("enc", enc)
        if new_enc != enc:
            print(f"  📖 图鉴: {enc} → {new_enc}")
    
    # Final sell
    raw = fish("sell all")
    print(f"\n🏁 结算: {raw.split(chr(10))[0]}")

if __name__ == "__main__":
    run()
