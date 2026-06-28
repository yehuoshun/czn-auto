"""
从 B站 wiki 批量抓取角色卡牌数据 v4
提取：card-name-inner / card-category alt / card-cost alt / card-desc-text
"""

import json, re, time, os, urllib.request, urllib.parse
from pathlib import Path

OUT_DIR = Path(__file__).parent.parent / "src" / "data" / "cards"
os.makedirs(OUT_DIR, exist_ok=True)

CHARACTERS = [
    "米卡", "蕾诺娅", "维罗妮卡", "卡利佩", "赛雷妮尔", "卢克",
    "卢卡斯", "凯隆", "卡修斯", "莉妲", "蕾伊", "友纪",
    "千鹤", "黛安娜", "蒂菲拉", "小春", "凛", "特莱莎",
    "欧文", "海德玛丽", "尼娅", "贝丽尔", "麦格纳", "绯",
    "九", "泰妮布里雅", "阿黛海特", "娜嘉", "雨果", "梅铃",
    "奥莱娅", "玛丽贝儿", "艾米尔", "赛琳娜",
]

WIKI_BASE = "https://wiki.biligame.com"


def fetch_page(char_name: str) -> str | None:
    url = f"{WIKI_BASE}/czn/{urllib.parse.quote(char_name)}"
    req = urllib.request.Request(url, headers={"User-Agent": "czn-auto-fetcher/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  ⚠️ 获取失败: {e}")
        return None


def parse_cards(html: str, char_name: str) -> dict | None:
    # 分别提取
    names = re.findall(r'class="card-name-inner">([^<]+)</span>', html)
    cats = re.findall(r'class="card-category"><img[^>]*alt="Icon category card ([^"]+)\.png"', html)
    costs = re.findall(r'alt="Cost (\d+)\.png"', html)
    descs_raw = re.findall(r'class="card-desc-text">(.*?)(?=</div>)', html, re.DOTALL)
    
    # 清理效果文本
    descs = []
    for d in descs_raw:
        d = re.sub(r'<[^>]+>', '', d).strip()
        d = d.replace('<br />', ' ').replace('<br/>', ' ')
        d = re.sub(r'\s+', ' ', d)
        descs.append(d)
    
    # 取前一半（数据重复了一次）
    n = len(names) // 2
    if n == 0:
        n = len(names)
    names = names[:n]
    cats = cats[:n]
    costs = costs[:n]
    descs = descs[:n]
    
    if not names:
        return None
    
    cards = {}
    seen = set()
    for i in range(min(len(names), len(cats), len(costs), len(descs))):
        name = names[i].strip()
        if name in seen or len(name) > 12:
            continue
        seen.add(name)
        cards[name] = {
            "type": cats[i],
            "cost": int(costs[i]),
            "effect": descs[i] if i < len(descs) else "",
        }
    
    if not cards:
        return None
    
    return {"角色": char_name, "卡牌": cards}


def main():
    success = 0
    for i, char in enumerate(CHARACTERS):
        print(f"\n[{i+1}/{len(CHARACTERS)}] {char}")
        html = fetch_page(char)
        if not html:
            continue
        
        data = parse_cards(html, char)
        if data:
            fpath = OUT_DIR / f"{char}.json"
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            card_names = list(data["卡牌"].keys())
            costs = [c["cost"] for c in data["卡牌"].values()]
            print(f"  ✅ {len(card_names)}张 | {costs}")
            success += 1
        else:
            print(f"  ❌ 未解析")
        
        time.sleep(1.0)
    
    print(f"\n完成: {success}/{len(CHARACTERS)}")


if __name__ == "__main__":
    main()