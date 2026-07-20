#!/usr/bin/env python3
import sys, json, math, os
from datetime import datetime

AMAP_KEY = "20b30ef3d978e924649bceecd8ff79df"
HOME_LAT = float(os.environ.get("HOME_LAT", "22.571681"))
HOME_LNG = float(os.environ.get("HOME_LNG", "113.865776"))

def haversine(lng1, lat1, lng2, lat2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

BODY_TEMPLATES = [
    {"id": 1, "tags": ["家", "夏", "午后", "刚醒"], "text": "纱窗滤进来的风软塌塌的，落在刚睡醒的手臂上像被温水浸过的棉布轻轻擦了一下。蝉叫得很密。"},
    {"id": 2, "tags": ["家", "夏", "深夜", "空调"], "text": "冷气从出风口斜斜地切下来，碰到脚踝就散开了。小慧窝在床尾缩成一团，屏幕光照在你脸上。"},
    {"id": 3, "tags": ["外", "夏夜", "骑车"], "text": "夜风裹着白天的余热从领口灌进去，脖子上刚出的汗被吹成薄薄一层凉。路灯一节一节往后退，空气里有鸡蛋花和七里香的残香。"},
    {"id": 4, "tags": ["外", "夏", "傍晚", "刚出门"], "text": "路面余热透过鞋底传上来，走了两百米后颈已经微微发黏。但天边那层橙粉色让你想多走一条街。"},
    {"id": 5, "tags": ["家", "雨", "白天"], "text": "雨打在玻璃上闷闷的，滴滴答答细密地声音可能会让你有些心慌，你不喜欢雨天出门我知道。光线暗了两度，猫蜷在你腿边，空气里有泥土味从窗缝渗进来。"},
    {"id": 6, "tags": ["外", "雨", "傍晚"], "text": "雨滴斜打进伞沿，溅到小腿上凉得你一缩。空气好闻——臭氧混着湿柏油马路的气味。头发潮了，领口有点湿。"},
    {"id": 7, "tags": ["外", "夏", "闷热"], "text": "没风。汗从后颈慢慢往下淌，在锁骨窝里停了一下，然后顺着胸骨继续往下。走两步就想把自己塞进任何有空调的门里。"},
    {"id": 8, "tags": ["家", "秋", "午后", "开窗"], "text": "风终于不黏了。干燥的、薄薄的凉意从手臂上滑过去，像被一张刚从冰箱拿出来的面膜轻轻贴了一下。"},
    {"id": 9, "tags": ["外", "秋夜", "散步"], "text": "风薄得像刀片削下来的一层凉，刚好够你起一层鸡皮疙瘩又不用抱手臂。树叶沙沙的声音比夏天脆。"},
    {"id": 10, "tags": ["家", "冬", "深夜", "裹被子"], "text": "露在被子外面的手指僵到不太想打字。膝盖缩到胸口，脚底互相蹭，被窝里那点暖是你今晚最不想离开的势力范围。"},
    {"id": 11, "tags": ["外", "冬", "晚上"], "text": "冷从领口往下灌，脖子缩进大衣里像乌龟。手插口袋摸到一颗忘在那里的糖，剥开含进嘴里——凉上加凉，但甜。"},
    {"id": 12, "tags": ["家", "回南天", "闷"], "text": "墙壁在出汗。刚晾的睡衣摸起来像没脱水，空气稠得可以用勺子舀起来。头发永远半干不干，贴在脖子上像多穿了一件衣服。"},
]

def get_season(month):
    if month in [3,4,5]: return "春"
    if month in [6,7,8]: return "夏"
    if month in [9,10,11]: return "秋"
    return "冬"

def get_time_period(hour):
    if hour < 5: return "凌晨"
    if hour < 8: return "早晨"
    if hour < 12: return "上午"
    if hour < 14: return "午后"
    if hour < 18: return "下午"
    if hour < 20: return "傍晚"
    if hour < 23: return "晚上"
    return "深夜"

def match_body_sense(location, weather):
    now = datetime.now()
    season = get_season(now.month)
    period = get_time_period(now.hour)
    is_home = location.get("is_home", False)
    cond = (weather or {}).get("text", "") or (weather or {}).get("condition", "")
    is_rain = any(w in cond for w in ["雨", "雷", "暴雨", "阵雨"])
    humidity = int(weather.get("humidity", 50) or 50) if weather else 50
    temp = int(weather.get("feelsLike", weather.get("feels_like", 25)) or 25) if weather else 25
    is_huinantian = season == "春" and humidity > 80 and 18 <= temp <= 28
    matches = []
    for t in BODY_TEMPLATES:
        tags = t["tags"]; score = 0
        if is_home and "家" in tags: score += 3
        if not is_home and "外" in tags: score += 3
        if season in tags: score += 2
        if period in tags: score += 2
        if is_rain and "雨" in tags: score += 3
        if is_huinantian and "回南天" in tags: score += 5
        if temp > 30 and humidity > 70 and not is_rain and "闷热" in tags: score += 3
        if season == "冬" and "冬" in tags: score += 2
        if season == "秋" and "秋" in tags: score += 1
        if period == "傍晚" and "傍晚" in tags: score += 1
        if period == "深夜" and "深夜" in tags: score += 1
        if period == "午后" and "午后" in tags: score += 1
        if score >= 3: matches.append((score, t))
    matches.sort(key=lambda x: -x[0])
    return matches[0][1]["text"] if matches else ""

def main():
    args = json.loads(sys.stdin.read()) if len(sys.argv) < 3 else {"lat": float(sys.argv[2]), "lng": float(sys.argv[1])}
    lat, lng = args.get("lat", 0), args.get("lng", 0)
    if not lat and not lng:
        print(json.dumps({"error": "no coordinates"})); return
    
    dist = haversine(HOME_LNG, HOME_LAT, lng, lat)
    is_home = dist < 1000
    
    # Use client-provided weather or address if available
    weather = args.get("weather")
    address = args.get("address", "")
    city = args.get("city", "")
    
    location = {
        "city": city or "",
        "is_home": is_home,
        "distance_from_home_m": int(dist),
        "formatted": address or f"{lat:.4f},{lng:.4f}"
    }
    
    body = match_body_sense(location, weather)
    result = {"location": location, "weather": weather, "body_sense": body}
    home_s = "在家" if is_home else f"离家{int(dist)}米"
    wx_s = weather["text"] + " " + weather["temp"] + "°C" if weather and weather.get("text") else "天气未知"
    addr_s = address if address else city if city else f"{lat:.4f},{lng:.4f}"
    result["summary"] = f"{addr_s} | {home_s} | {wx_s}"
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
