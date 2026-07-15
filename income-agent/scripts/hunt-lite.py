#!/usr/bin/env python3
"""Parse FL.ru project listings and score leads without LLM."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "references"
OUT_JSON = REFS / "leads-candidates.json"
SEEN_JSON = REFS / "leads-seen.json"

BASE = "https://www.fl.ru"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

CATEGORIES = [
    ("AI", f"{BASE}/projects/category/ai-iskusstvenniy-intellekt/"),
    ("Лендинги", f"{BASE}/projects/category/saity/landing/"),
    ("SMM", f"{BASE}/projects/category/reklama-marketing/smm-marketing-v-sotssetyah/"),
    ("SEO", f"{BASE}/projects/category/prodvizhenie-saitov-seo/"),
]

HIGH_FIT = re.compile(
    r"ai|ии|нейросет|нейро|инфлюенс|контент.?завод|чат.?бот|telegram|"
    r"лендинг|сайт|seo|sitemap|автоматиз|агент|prompt|промпт|"
    r"heygen|sora|вайб|vibe|ассистент|заявк",
    re.I,
)
MEDIUM_FIT = re.compile(r"презентац|копирайт|smm|таргет|дизайн|видео", re.I)
RED_FLAGS = re.compile(
    r"бесплатно|для портфолио|потом заплат|без оплаты|тестовое бесплатно|"
    r"соосновател|cto|стажер|intern",
    re.I,
)
LOW_BUDGET = re.compile(r"до\s*(\d[\d\s]*)\s*₽|(\d[\d\s]*)\s*₽\s*/\s*мес", re.I)


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fetch_html(url: str, cookie_jar: dict[str, str]) -> str:
    headers = {"User-Agent": UA, "Accept-Language": "ru-RU,ru;q=0.9"}
    if cookie_jar:
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookie_jar.items())
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as resp:
        for header in resp.headers.get_all("Set-Cookie", []) or []:
            part = header.split(";", 1)[0]
            if "=" in part:
                k, v = part.split("=", 1)
                cookie_jar[k.strip()] = v.strip()
        return resp.read().decode("utf-8", errors="replace")


def parse_budget_num(budget: str) -> int | None:
    if not budget or budget == "не указан":
        return None
    if "договор" in budget.lower() or "собесед" in budget.lower():
        return None
    m = re.search(r"(\d[\d\s]*)", budget.replace("\xa0", " "))
    if not m:
        return None
    return int(re.sub(r"\s", "", m.group(1)))


def score_lead(title: str, budget: str, category: str) -> tuple[int, list[str]]:
    text = f"{title} {category}"
    notes: list[str] = []
    score = 0

    high_hits = len(HIGH_FIT.findall(text))
    if high_hits >= 2:
        score += 3
        notes.append("high-fit-x2")
    elif high_hits == 1:
        score += 2
        notes.append("high-fit")
    elif MEDIUM_FIT.search(text):
        score += 1
        notes.append("medium-fit")

    if category == "AI":
        score += 1
        notes.append("ai-category")
    if re.search(r"агент|ассистент|контент.?завод|ai.?креатор|вайб|prompt", text, re.I):
        score += 1
        notes.append("priority-niche")

    amount = parse_budget_num(budget)
    if amount is None:
        score += 1
        notes.append("budget-negotiable")
    elif amount >= 45000:
        score += 2
        notes.append("budget-ok")
    elif amount >= 15000:
        score += 1
        notes.append("budget-mid")
    else:
        notes.append("budget-low")

    low = LOW_BUDGET.search(budget)
    if low:
        nums = [n for n in low.groups() if n]
        if nums:
            val = int(re.sub(r"\s", "", nums[0]))
            if val < 15000:
                score -= 2
                notes.append("red-flag-low-pay")

    score += 1  # FL.ru = remote-friendly

    if len(title) > 12:
        score += 1
    if len(title) > 25:
        score += 1

    if RED_FLAGS.search(text):
        score -= 3
        notes.append("red-flag")

    return max(0, min(10, score)), notes


def parse_projects(html: str, category: str) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    for block in re.split(r"(?=<h2)", html):
        link = re.search(r'href="(/projects/(\d+)/[^"]+\.html)"', block)
        if not link:
            continue
        path, pid = link.group(1), link.group(2)
        if pid in seen:
            continue
        seen.add(pid)

        title_m = re.search(
            rf'<h2[^>]*>\s*<a[^>]+href="/projects/{pid}[^"]*"[^>]*>([^<]+)</a>',
            block,
            re.S,
        )
        title = unescape(re.sub(r"\s+", " ", title_m.group(1))).strip() if title_m else pid
        if title.lower() == "откликнуться":
            title = path.rsplit("/", 1)[-1].replace(".html", "").replace("-", " ")

        bud = re.search(
            r"(\d[\d\s\u00a0–-]*\s*₽|до\s*\d[\d\s\u00a0]*\s*₽|по договоренности|по результатам собеседования)",
            block,
            re.I,
        )
        budget = bud.group(1).replace("\xa0", " ").strip() if bud else "не указан"
        resp = re.search(r"(\d+)\s+ответ", block)
        responses = int(resp.group(1)) if resp else 0

        sc, notes = score_lead(title, budget, category)
        items.append(
            {
                "id": pid,
                "title": title,
                "budget": budget,
                "budget_rub": parse_budget_num(budget),
                "category": category,
                "responses": responses,
                "score": sc,
                "notes": notes,
                "url": BASE + path,
            }
        )
    return items


def hunt(min_score: int) -> list[dict]:
    cookies: dict[str, str] = {}
    all_items: dict[str, dict] = {}
    for cat_name, url in CATEGORIES:
        try:
            html = fetch_html(url, cookies)
        except urllib.error.URLError as exc:
            print(f"WARN fetch {cat_name}: {exc}", file=sys.stderr)
            continue
        for item in parse_projects(html, cat_name):
            prev = all_items.get(item["id"])
            if not prev or item["score"] > prev["score"]:
                all_items[item["id"]] = item

    seen = set(load_json(SEEN_JSON, {}).get("ids", []))
    leads = [x for x in all_items.values() if x["score"] >= min_score and x["id"] not in seen]
    leads.sort(key=lambda x: (-x["score"], x["responses"]))
    return leads


def format_telegram(leads: list[dict], min_score: int) -> str:
    now = datetime.now(timezone.utc).astimezone().strftime("%d.%m.%Y %H:%M")
    if not leads:
        return f"Income Agent · {now}\n\nНовых лидов score≥{min_score} нет. Grok не нужен."

    lines = [f"Income Agent · {now}", f"Новых лидов: {len(leads)} (score≥{min_score})", ""]
    for i, lead in enumerate(leads[:5], 1):
        lines.append(f"{i}. [{lead['score']}/10] {lead['title'][:60]}")
        lines.append(f"   {lead['budget']} · {lead['responses']} откл. · {lead['category']}")
        lines.append(f"   {lead['url']}")
        lines.append("")
    lines.append("Grok: /income-agent propose 1,2,3 — только если откликаемся.")
    return "\n".join(lines)


def send_telegram(text: str) -> None:
    token = os.environ.get("INCOME_AGENT_TG_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("INCOME_AGENT_TG_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("SKIP telegram: set INCOME_AGENT_TG_BOT_TOKEN and INCOME_AGENT_TG_CHAT_ID", file=sys.stderr)
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text, "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(url, data=payload, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
        if not body.get("ok"):
            raise RuntimeError(body)


def mark_seen(ids: list[str]) -> None:
    data = load_json(SEEN_JSON, {"ids": []})
    merged = list(dict.fromkeys(data.get("ids", []) + ids))
    data["ids"] = merged[-500:]
    data["updated"] = datetime.now(timezone.utc).isoformat()
    save_json(SEEN_JSON, data)


def main() -> int:
    parser = argparse.ArgumentParser(description="FL.ru hunt without LLM")
    parser.add_argument("--min-score", type=int, default=7, help="Minimum lead score (0-10)")
    parser.add_argument("--telegram", action="store_true", help="Send digest to Telegram")
    parser.add_argument("--mark-seen", action="store_true", help="Mark found IDs as seen")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args()

    leads = hunt(args.min_score)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "min_score": args.min_score,
        "count": len(leads),
        "leads": leads,
    }
    save_json(OUT_JSON, payload)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    digest = format_telegram(leads, args.min_score)
    print(digest)

    if args.telegram:
        send_telegram(digest)

    if args.mark_seen and leads:
        mark_seen([lead["id"] for lead in leads])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())