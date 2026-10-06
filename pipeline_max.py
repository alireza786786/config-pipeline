import base64
import json
import os
import re
import socket
import time
import urllib.parse
import requests

SOURCE_MAX = os.getenv("SOURCE_Max")
CONFIG_REGEX = re.compile(r"(?:vmess|vless|trojan|ss)://[^\s<>'\"]+")

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
    "us": ("🇺🇸", "آمریکا", "نیویورک"),
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
    if not text:
        return None
    for flag_emoji, info in FLAGS.items():
        if flag_emoji in text:
            return info
    low = text.lower()
    for key, info in COUNTRY_MAP.items():
        if re.search(r'\b' + re.escape(key) + r'\b', low) or key in low:
            return info
    return None

def get_ip_info(host: str):
    try:
        res = requests.get(
            f"http://ip-api.com/json/{host}?fields=status,country,countryCode,city",
            timeout=2
        ).json()
        if res.get("status") == "success":
            code = res.get("countryCode", "").lower()
            if code in COUNTRY_MAP:
                return COUNTRY_MAP[code]
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

def parse_host_port(config_str: str):
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
    """تست باز بودن پورت و محاسبه پینگ واقعی به میلی‌ثانیه"""
    if not host or not port:
        return -1
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)
        sock.connect((host, port))
        sock.close()
        return int((time.time() - start_time) * 1000)
    except Exception:
        return -1

def get_config_fingerprint(cfg: str) -> str:
    try:
        if cfg.startswith("vmess://"):
            b64_part = cfg.replace("vmess://", "")
            padded = b64_part + "=" * (-len(b64_part) % 4)
            data = json.loads(base64.b64decode(padded).decode("utf-8", errors="ignore"))
            return f"vmess:{data.get('add')}:{data.get('port')}:{data.get('id')}:{data.get('path', '')}"
        else:
            return cfg.split("#")[0].strip()
    except Exception:
        return cfg

def format_vmess(config_str: str, ping_val: int) -> str:
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

        remark = f"👉🆔@Goodbaye_filtering 📡{flag} {country} ®️{city} 🅿️ping:{ping_val}ms ⚡{cap}"
        data["ps"] = remark
        
        new_b64 = base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")
        return f"vmess://{new_b64}"
    except Exception:
        return None

def format_uri(config_str: str, ping_val: int) -> str:
    try:
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

        remark = f"👉🆔@Goodbaye_filtering 📡{flag} {country} ®️{city} 🅿️ping:{ping_val}ms ⚡{cap}"
        clean_url = config_str.split("#")[0]
        return f"{clean_url}#{urllib.parse.quote(remark)}"
    except Exception:
        return None

def fetch_and_process():
    if not SOURCE_MAX:
        print("SOURCE_Max secret is not set.")
        return

    content = ""
    if SOURCE_MAX.startswith("http://") or SOURCE_MAX.startswith("https://"):
        try:
            r = requests.get(SOURCE_MAX.strip(), timeout=15)
            if r.status_code == 200:
                content = r.text
        except Exception as e:
            print(f"Error fetching SOURCE_Max: {e}")
            return
    else:
        content = SOURCE_MAX

    if not content.startswith("vless://") and not content.startswith("vmess://"):
        try:
            decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
            if "://" in decoded:
                content = decoded
        except Exception:
            pass

    found = CONFIG_REGEX.findall(content)
    
    # حذف تکراری‌ها
    seen_fingerprints = set()
    unique_candidates = []
    for cfg in found:
        fp = get_config_fingerprint(cfg)
        if fp not in seen_fingerprints:
            seen_fingerprints.add(fp)
            unique_candidates.append(cfg)

    print(f"Found {len(unique_candidates)} unique candidates from SOURCE_Max. Testing connections...")

    verified_configs = []
    
    # تست پینگ واقعی و فیلتر سرورهای خاموش
    for cfg in unique_candidates:
        host, port = parse_host_port(cfg)
        if not host or not port:
            continue
        
        latency = test_real_ping(host, port)
        if latency > 0:
            if cfg.startswith("vmess://"):
                formatted = format_vmess(cfg, latency)
            else:
                formatted = format_uri(cfg, latency)
            
            if formatted:
                cap = detect_capability(cfg)
                proto = "vmess" if cfg.startswith("vmess://") else ("vless" if cfg.startswith("vless://") else ("trojan" if cfg.startswith("trojan://") else "ss"))
                verified_configs.append((latency, proto, cap, formatted))

    # سورت بر اساس بهترین پینگ (کمترین تاخیر)
    verified_configs.sort(key=lambda x: x[0])
    print(f"Total alive and verified configs: {len(verified_configs)}")

    if not verified_configs:
        print("No alive configs found.")
        return

    # تفکیک بر اساس پروتکل و قابلیت
    all_list = [c[3] for c in verified_configs]
    reality_list = [c[3] for c in verified_configs if c[2] == "Reality"]
    vless_list = [c[3] for c in verified_configs if c[1] == "vless"]
    vmess_list = [c[3] for c in verified_configs if c[1] == "vmess"]
    trojan_list = [c[3] for c in verified_configs if c[1] == "trojan"]

    # ذخیره در فایل‌های مجزا در شاخه اصلی مخزن
    files_to_write = {
        "configs_all.txt": all_list,
        "configs_reality.txt": reality_list,
        "configs_vless.txt": vless_list,
        "configs_vmess.txt": vmess_list,
        "configs_trojan.txt": trojan_list,
    }

    for filename, lines in files_to_write.items():
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Saved {len(lines)} configs to {filename}")

if __name__ == "__main__":
    fetch_and_process()
