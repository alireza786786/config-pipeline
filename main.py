import base64
import json
import os
import re
import socket
import time
import urllib.parse
from datetime import datetime
import requests

# خواندن متغیرهای محرمانه از گیت‌هاب
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# منابع فعال و به‌روز کانفیگ‌ها
GITHUB_SOURCES = [
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub1.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub2.txt",
    "https://raw.githubusercontent.com/LalatinaHub/Mineral/master/result/nodes",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/reality",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/vless",
]

TELEGRAM_CHANNELS = [
    "v2rayNG_VPNofficial",
    "v2ray_configs_pool",
    "PrivateVPNOfficial",
    "Outline_Vpn",
]

CONFIG_REGEX = re.compile(r"(?:vmess|vless|trojan|ss)://[^\s<>'\"]+")

def get_flag(country_code: str) -> str:
    if not country_code or len(country_code) != 2:
        return "🌐"
    return "".join(chr(127397 + ord(c)) for c in country_code.upper())

def get_ip_info(host: str):
    """استخراج پرچم، کشور و شهر سرور"""
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
    """تشخیص نوع قابلیت کانفیگ"""
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

def parse_host_port(config_str: str):
    """استخراج آدرس و پورت سرور جهت تست اتصال واقعی"""
    try:
        if config_str.startswith("vmess://"):
            b64_part = config_str.replace("vmess://", "")
            padded = b64_part + "=" * (-len(b64_part) % 4)
            data = json.loads(base64.b64decode(padded).decode("utf-8", errors="ignore"))
            return data.get("add", ""), int(data.get("port", 443))
        else:
            parsed = urllib.parse.urlparse(config_str)
            return parsed.hostname, int(parsed.port or 443)
    except Exception:
        return None, None

def test_real_ping(host: str, port: int) -> int:
    """تست واقعی باز بودن پورت و محاسبه پینگ بر حسب میلی‌ثانیه"""
    if not host or not port:
        return -1
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)  # اگر در ۱.۵ ثانیه پاسخ ندهد سرور مرده است
        sock.connect((host, port))
        sock.close()
        latency = int((time.time() - start_time) * 1000)
        return latency
    except Exception:
        return -1

def format_vmess(config_str: str, ping_val: int) -> str:
    """قالب‌بندی کانفیگ VMess طبق الگوی پین‌شده"""
    try:
        b64_part = config_str.replace("vmess://", "")
        padded = b64_part + "=" * (-len(b64_part) % 4)
        data = json.loads(base64.b64decode(padded).decode("utf-8", errors="ignore"))
        
        host = data.get("add", "")
        flag, country, city = get_ip_info(host)
        cap = detect_capability(config_str)

        remark = f"👉🆔@Goodbaye_filtering 📡{flag} {country} ®️{city} 🅿️ping:{ping_val}ms ⚡{cap}"
        data["ps"] = remark
        
        new_b64 = base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")
        return f"vmess://{new_b64}"
    except Exception:
        return None

def format_uri(config_str: str, ping_val: int) -> str:
    """قالب‌بندی کانفیگ‌های VLESS, Trojan, SS طبق الگوی پین‌شده"""
    try:
        parsed = urllib.parse.urlparse(config_str)
        host = parsed.hostname or "1.1.1.1"
        flag, country, city = get_ip_info(host)
        cap = detect_capability(config_str)

        remark = f"👉🆔@Goodbaye_filtering 📡{flag} {country} ®️{city} 🅿️ping:{ping_val}ms ⚡{cap}"
        clean_url = config_str.split("#")[0]
        return f"{clean_url}#{urllib.parse.quote(remark)}"
    except Exception:
        return None

def collect_and_verify():
    """جمع‌آوری و پالایش بر اساس تست واقعی پینگ"""
    raw_configs = []

    # ۱. استخراج از سورس‌های گیت‌هاب
    for g_url in GITHUB_SOURCES:
        try:
            r = requests.get(g_url, timeout=6)
            if r.status_code == 200:
                text = r.text
                if not text.startswith("vless://") and not text.startswith("vmess://"):
                    try:
                        text = base64.b64decode(text).decode("utf-8", errors="ignore")
                    except Exception:
                        pass
                raw_configs.extend(CONFIG_REGEX.findall(text))
        except Exception:
            pass

    # ۲. استخراج از کانال‌های تلگرام
    for ch in TELEGRAM_CHANNELS:
        try:
            r = requests.get(f"https://t.me/s/{ch}", timeout=6)
            if r.status_code == 200:
                raw_configs.extend(CONFIG_REGEX.findall(r.text))
        except Exception:
            pass

    unique_candidates = list(dict.fromkeys(raw_configs))
    print(f"Total candidate configs collected: {len(unique_candidates)}")

    alive_configs = []

    # ۳. فیلتر کردن کانفیگ‌های خاموش و ثبت پینگ واقعی
    for cfg in unique_candidates:
        host, port = parse_host_port(cfg)
        if not host or not port:
            continue

        latency = test_real_ping(host, port)
        if latency > 0:  # فقط سرورهایی که اتصال واقعی دادند
            if cfg.startswith("vmess://"):
                formatted = format_vmess(cfg, latency)
            else:
                formatted = format_uri(cfg, latency)

            if formatted:
                alive_configs.append((latency, formatted))

            # جمع‌آوری تا سقف ۵۰ کانفیگ فعال و سالم
            if len(alive_configs) >= 50:
                break

    # سورت بر اساس بهترین پینگ (کمترین تاخیر)
    alive_configs.sort(key=lambda x: x[0])
    return [c[1] for c in alive_configs]

def send_to_telegram(file_path: str, count: int):
    """ارسال به تلگرام با کپشن و دکمه‌های شیشه‌ای پین‌شده"""
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram Credentials not found.")
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    caption = (
        "🔰 پکیج اختصاصی کانفیگ‌های همراه‌اول (MCI)\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 مشخصات و آمار فایل:\n"
        f"🔹 تعداد کل کانفیگ‌ها: {count} عدد (تست‌شده و زنده)\n"
        "🔹 پروتکل‌ها: VLESS | VMess | Trojan | Reality\n"
        "🔹 وضعیت سلامت: تست سوکت واقعی و پینگ تاییدشده\n"
        "🔹 برچسب اختصاصی: @Goodbaye_filtering\n"
        f"🔹 زمان به‌روزرسانی: {now_str}\n\n"
        "⚡️ ویژگی‌ها:\n"
        "✔️ دارای تفکیک پرچم و نام کشورها\n"
        "✔️ پینگ واقعی محاسبه‌شده بر حسب میلی‌ثانیه\n"
        "✔️ حاوی فناوری Reality و هسته‌های نوین\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📱 قابل استفاده در کلاینت‌های:\n"
        "v2rayNG | Hiddify | Nekoray | Streisand | Shadowrocket\n\n"
        "👉🆔 @Goodbaye_filtering"
    )

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "📢 کانال رسمی", "url": "https://t.me/Goodbaye_filtering"},
                {"text": "💬 گروه چت و گفت‌وگو", "url": "https://t.me/CONFIG_V2RAY_VIP"}
            ],
            [
                {
                    "text": "👥 معرفی کانال به دوستان خود",
                    "url": "https://t.me/share/url?url=https://t.me/Goodbaye_filtering&text=پکیج کانفیگ‌های اختصاصی همراه اول"
                }
            ]
        ]
    }

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(file_path, "rb") as doc:
        files = {"document": ("MCI_Configs.txt", doc)}
        data = {
            "chat_id": CHAT_ID,
            "caption": caption,
            "reply_markup": json.dumps(reply_markup)
        }
        res = requests.post(url, data=data, files=files, timeout=30)
        print("Telegram response status:", res.status_code)

def main():
    configs = collect_and_verify()
    if not configs:
        print("No alive configs found right now.")
        return

    file_name = "MCI_Configs.txt"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write("\n".join(configs))

    send_to_telegram(file_name, len(configs))

if __name__ == "__main__":
    main()
