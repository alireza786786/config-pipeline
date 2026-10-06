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

def get_flag(country_code: str) -> str:
    if not country_code or len(country_code) != 2:
        return "🌐"
    return "".join(chr(127397 + ord(c)) for c in country_code.upper())

def get_ip_info(host: str):
    try:
        res = requests.get(
            f"http://ip-api.com/json/{host}?fields=status,country,countryCode,city",
            timeout=2
        ).json()
        if res.get("status") == "success":
            flag = get_flag(res.get("countryCode", ""))
            return flag, res.get("country", "Unknown"), res.get("city", "Unknown")
    except Exception:
        pass
    return "🌐", "Global", "Edge"

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
        
        host = data.get("add", "")
        flag, country, city = get_ip_info(host)
        cap = detect_capability(config_str)

        remark = f"👉🆔@Goodbaye_filtering 📡{flag} {country} ®️{city} 🅿️ping:85ms ⚡{cap}"
        data["ps"] = remark
        
        new_b64 = base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")
        return f"vmess://{new_b64}"
    except Exception:
        return config_str

def format_uri(config_str: str) -> str:
    try:
        parsed = urllib.parse.urlparse(config_str)
        host = parsed.hostname or "1.1.1.1"
        flag, country, city = get_ip_info(host)
        cap = detect_capability(config_str)

        remark = f"👉🆔@Goodbaye_filtering 📡{flag} {country} ®️{city} 🅿️ping:80ms ⚡{cap}"
        clean_url = config_str.split("#")[0]
        return f"{clean_url}#{urllib.parse.quote(remark)}"
    except Exception:
        return config_str

def fetch_source_configs():
    if not SOURCE_MCI:
        print("SOURCE_MCI secret is not defined.")
        return []

    content = ""
    if SOURCE_MCI.startswith("http://") or SOURCE_MCI.startswith("https://"):
        try:
            r = requests.get(SOURCE_MCI.strip(), timeout=15)
            if r.status_code == 200:
                content = r.text
        except Exception as e:
            print(f"Error fetching SOURCE_MCI: {e}")
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
    print(f"Total extracted from SOURCE_MCI: {len(unique_cfgs)}")

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

    # تقسیم هوشمند کانفیگ‌ها به دسته‌هایی که هرگز از سقف تلگرام تجاوز نکنند
    batches = []
    current_batch = []
    current_len = 0

    for cfg in configs:
        cfg_len = len(html.escape(cfg)) + 4
        # سقف امن ۳۰۰۰ کاراکتر برای هر پیام
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
            "👇 <i>برای مشاهده و کپی یکجای کانفیگ‌ها روی کادر زیر ضربه بزنید:</i>\n\n"
            f"<blockquote expandable><code>{safe_text}</code></blockquote>\n\n"
            "#همراه_اول"
        )

        data = {
            "chat_id": CHAT_ID,
            "text": message_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        res = requests.post(url, data=data, timeout=25)
        print(f"Telegram send status part {idx}:", res.status_code, res.text)
        time.sleep(1)

def main():
    configs = fetch_source_configs()
    if configs:
        send_expandable_to_telegram(configs)
    else:
        print("No configs found.")

if __name__ == "__main__":
    main()
