import base64
import html
import json
import os
import re
import time
import urllib.parse
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SOURCE_MCI = os.getenv("SOURCE_MCI")

CONFIG_REGEX = re.compile(r"(?:vmess|vless|trojan|ss)://[^\s<>'\"]+")

# دیکشنری هوشمند برای شناسایی کشورها از متن اولیه و تبدیل به فارسی
COUNTRY_MAP = {
    "de": ("🇩🇪", "آلمان", "فرانکفورت"),
    "germany": ("🇩🇪", "آلمان", "فرانکفورت"),
    "آلمان": ("🇩🇪", "آلمان", "فرانکفورت"),
    "nl": ("🇳🇱", "هلند", "آمستردام"),
    "netherlands": ("🇳🇱", "هلند", "آمستردام"),
    "هلند": ("🇳🇱", "هلند", "آمستردام"),
    "fr": ("🇫🇷", "فرانسه", "پاریس"),
    "france": ("🇫🇷", "فرانسه", "پاریس"),
    "فرانسه": ("🇫🇷", "فرانسه", "پاریس"),
    "gb": ("🇬🇧", "انگلیس", "لندن"),
    "uk": ("🇬🇧", "انگلیس", "لندن"),
    "united kingdom": ("🇬🇧", "انگلیس", "لندن"),
    "انگلیس": ("🇬🇧", "انگلیس", "لندن"),
    "bریتانیا": ("🇬🇧", "انگلیس", "لندن"),
    "us": ("🇺🇸", "آمریکا", "واشنگتن"),
    "usa": ("🇺🇸", "آمریکا", "نیویورک"),
    "united states": ("🇺🇸", "آمریکا", "نیویورک"),
    "آمریکا": ("🇺🇸", "آمریکا", "نیویورک"),
    "tr": ("🇹🇷", "ترکیه", "استانبول"),
    "turkey": ("🇹🇷", "ترکیه", "استانبول"),
    "ترکیه": ("🇹🇷", "ترکیه", "استانبول"),
    "fi": ("🇫🇮", "فنلاند", "هلسینکی"),
    "finland": ("🇫🇮", "فنلاند", "هلسینکی"),
    "فنلاند": ("🇫🇮", "فنلاند", "هلسینکی"),
    "pl": ("🇵🇱", "لهستان", "ورشو"),
    "poland": ("🇵🇱", "لهستان", "ورشو"),
    "لهستان": ("🇵🇱", "لهستان", "ورشو"),
    "ru": ("🇷🇺", "روسیه", "مسکو"),
    "russia": ("🇷🇺", "روسیه", "مسکو"),
    "روسیه": ("🇷🇺", "روسیه", "مسکو"),
    "se": ("🇸🇪", "سوئد", "استکهلم"),
    "sweden": ("🇸🇪", "سوئد", "استکهلم"),
    "سوئد": ("🇸🇪", "سوئد", "استکهلم"),
    "ch": ("🇨🇭", "سوئیس", "زوریخ"),
    "switzerland": ("🇨🇭", "سوئیس", "زوریخ"),
    "سوئیس": ("🇨🇭", "سوئیس", "زوریخ"),
    "it": ("🇮🇹", "ایتالیا", "میلان"),
    "italy": ("🇮🇹", "ایتالیا", "میلان"),
    "ایتالیا": ("🇮🇹", "ایتالیا", "میلان"),
    "ae": ("🇦🇪", "امارات", "دبی"),
    "uae": ("🇦🇪", "امارات", "دبی"),
    "امارات": ("🇦🇪", "امارات", "دبی"),
}

# ایموجی پرچم‌های دنیا
FLAGS = {
    "🇩🇪": ("🇩🇪", "آلمان", "فرانکفورت"),
    "🇳🇱": ("🇳🇱", "هلند", "آمستردام"),
    "🇫🇷": ("🇫🇷", "فرانسه", "پاریس"),
    "🇬🇧": ("🇬🇧", "انگلیس", "لندن"),
    "🇺🇸": ("🇺🇸", "آمریکا", "نیویورک"),
    "🇹🇷": ("🇹🇷", "ترکیه", "استانبول"),
    "🇫🇮": ("🇫🇮", "فنلاند", "هلسینکی"),
    "🇵🇱": ("🇵🇱", "لهستان", "ورشو"),
    "🇨🇦": ("🇨🇦", "کانادا", "تورنتو"),
    "🇸🇪": ("🇸🇪", "سوئد", "استکهلم"),
    "🇨🇭": ("🇨🇭", "سوئیس", "زوریخ"),
    "🇮🇹": ("🇮🇹", "ایتالیا", "میلان"),
}

def extract_geo_from_text(text: str):
    """جستجوی پرچم یا نام کشور در عنوان اولیه کانفیگ"""
    if not text:
        return None
    # ۱. جستجوی مستقیم پرچم‌های ایموجی
    for flag_emoji, info in FLAGS.items():
        if flag_emoji in text:
            return info
    # ۲. جستجوی کلمات کلیدی کشورها
    low = text.lower()
    for key, info in COUNTRY_MAP.items():
        if re.search(r'\b' + re.escape(key) + r'\b', low) or key in low:
            return info
    return None

def get_ip_info(host: str):
    """استعلام اینترنتی در صورت مشخص نبودن در عنوان"""
    try:
        res = requests.get(
            f"http://ip-api.com/json/{host}?fields=status,country,countryCode,city",
            timeout=2
        ).json()
        if res.get("status") == "success":
            code = res.get("countryCode", "").lower()
            if code in COUNTRY_MAP:
                return COUNTRY_MAP[code]
            # در صورتی که کشور دیگری بود
            flag = "".join(chr(127397 + ord(c)) for c in code.upper())
            return flag, res.get("country", "ناشناس"), res.get("city", "مرکزی")
    except Exception:
        pass
    return "🌐", "اروپا", "مرکزی"

def detect_capability(config: str) -> str:
    low = config.lower()
    if "reality" in low:
        return "Reality"
    if "grpc" in low:
        return "gRPC"
    if "ws" in low or "websocket" in low:
        return "WebSocket"
    if "tcp" in low:
        return "TCP"
    return "Direct"

def format_vmess(config_str: str) -> str:
    try:
        b64_part = config_str.replace("vmess://", "")
        padded = b64_part + "=" * (-len(b64_part) % 4)
        data = json.loads(base64.b64decode(padded).decode("utf-8", errors="ignore"))
        
        orig_ps = data.get("ps", "")
        geo = extract_geo_from_text(orig_ps)
        if not geo:
            host = data.get("add", "")
            geo = get_ip_info(host)

        flag, country, city = geo
        cap = detect_capability(config_str)

        remark = f"👉🆔@Goodbaye_filtering 📡{flag} {country} ®️{city} 🅿️ping:85ms ⚡{cap}"
        data["ps"] = remark
        
        new_b64 = base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")
        return f"vmess://{new_b64}"
    except Exception:
        return config_str

def format_uri(config_str: str) -> str:
    try:
        # بررسی نام اولیه بعد از علامت #
        orig_remark = ""
        if "#" in config_str:
            orig_remark = urllib.parse.unquote(config_str.split("#", 1)[1])

        geo = extract_geo_from_text(orig_remark)
        if not geo:
            parsed = urllib.parse.urlparse(config_str)
            host = parsed.hostname or "1.1.1.1"
            geo = get_ip_info(host)

        flag, country, city = geo
        cap = detect_capability(config_str)

        remark = f"👉🆔@Goodbaye_filtering 📡{flag} {country} ®️{city} 🅿️ping:80ms ⚡{cap}"
        clean_url = config_str.split("#")[0]
        return f"{clean_url}#{urllib.parse.quote(remark)}"
    except Exception:
        return config_str

def fetch_source_configs():
    if not SOURCE_MCI:
        return []

    content = ""
    if SOURCE_MCI.startswith("http://") or SOURCE_MCI.startswith("https://"):
        try:
            r = requests.get(SOURCE_MCI.strip(), timeout=15)
            if r.status_code == 200:
                content = r.text
        except Exception:
            return []
    else:
        content = SOURCE_MCI

    if not content.startswith("vless://") and not content.startswith("vmess://"):
        try:
            decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
            if "://" in decoded:
                content = decoded
        except Exception:
            pass

    found = CONFIG_REGEX.findall(content)
    unique_cfgs = list(dict.fromkeys(found))

    formatted_list = []
    for cfg in unique_cfgs:
        if cfg.startswith("vmess://"):
            formatted_list.append(format_vmess(cfg))
        else:
            formatted_list.append(format_uri(cfg))

    return formatted_list

def send_expandable_to_telegram(configs):
    if not BOT_TOKEN or not CHAT_ID or not configs:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    batches = []
    current_batch = []
    current_len = 0

    for cfg in configs:
        cfg_len = len(html.escape(cfg)) + 4
        if current_batch and (current_len + cfg_len > 3000):
            batches.append(current_batch)
            current_batch = [cfg]
            current_len = cfg_len
        else:
            current_batch.append(cfg)
            current_len += cfg_len

    if current_batch:
        batches.append(current_batch)

    total_parts = len(batches)
    for idx, batch in enumerate(batches, 1):
        safe_text = html.escape("\n\n".join(batch))
        part_tag = f" (بخش {idx} از {total_parts})" if total_parts > 1 else ""

        message_text = (
            f"🔰 <b>پکیج کانفیگ‌های اختصاصی همراه اول{part_tag}</b>\n"
            "👉🆔 <b>@Goodbaye_filtering</b>\n"
            "👇 <i>برای مشاهده و کپی یکجای کانفیگ‌ها روی کادر زیر ضربه بزنید:</i>\n\n"
            f"<blockquote expandable><code>{safe_text}</code></blockquote>\n\n"
            "#همراه_اول\n"
            "👉🆔 @Goodbaye_filtering"
        )

        data = {
            "chat_id": CHAT_ID,
            "text": message_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        requests.post(url, data=data, timeout=25)
        time.sleep(1)

def main():
    configs = fetch_source_configs()
    if configs:
        send_expandable_to_telegram(configs)

if __name__ == "__main__":
    main()
