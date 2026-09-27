"""
nlp_utils.py
ฟังก์ชัน NLP ทั้งหมดของ Smart IT Ticket Classifier
ทุกหน้าในแอปเรียกใช้ analyze_ticket() จากไฟล์นี้

Pipeline:
  1. Regex & Cleansing        -> remove_pii(), clean_text()
  2. Normalization            -> normalize_text(), SYNONYMS
  3. Tokenization + Stopwords -> process_tokens()
  4. Topic Identification     -> classify_topic()
  5. Priority Detection       -> detect_priority()
  6. NER (rule-based) + POS   -> extract_entities(), extract_keywords_pos()
"""

import re
from functools import lru_cache

from pythainlp.corpus import thai_stopwords, thai_words
from pythainlp.tokenize import word_tokenize
from pythainlp.util import dict_trie

# ---------------------------------------------------------------------------
# 1) Regex & Cleansing
# ---------------------------------------------------------------------------
URL_RE = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# รองรับ 0812345678, 081-234-5678, 02 123 4567, +66812345678, +66 81 234 5678
PHONE_RE = re.compile(r"(\+66[\s-]?|0)\d{1,2}[\s-]?\d{3}[\s-]?\d{3,4}")
# คำนำหน้าเบอร์โทรที่ค้างอยู่หลังลบเบอร์ เช่น "โทร", "เบอร์", "tel"
PHONE_PREFIX_RE = re.compile(r"(โทร(ศัพท์)?|เบอร์(โทร)?|tel\.?|call)\s*[:：]?\s*(?=\s|$)", re.IGNORECASE)


def remove_pii(text: str) -> tuple[str, list[str]]:
    """ลบ URL, อีเมล, เบอร์โทร ออกจากข้อความ และคืนรายการสิ่งที่ถูกลบ"""
    removed = []
    for label, pattern in (("URL", URL_RE), ("อีเมล", EMAIL_RE), ("เบอร์โทร", PHONE_RE)):
        for m in pattern.finditer(text):
            removed.append(f"{label}: {m.group(0).strip()}")
        text = pattern.sub(" ", text)
    text = PHONE_PREFIX_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip(), removed


def clean_text(text: str) -> str:
    """ลบเครื่องหมาย/สัญลักษณ์ เหลือเฉพาะตัวอักษรไทย อังกฤษ ตัวเลข และช่องว่าง"""
    text = re.sub(r"[^\w\s\u0E00-\u0E7F]", "", text)  # Wi-Fi -> WiFi
    text = text.replace("_", " ")
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# 2) Normalization: คำลากเสียง ไม้ยมก ตัวพิมพ์ และคำสะกดหลายแบบ
# ---------------------------------------------------------------------------
SYNONYMS = {
    # network
    "ไวไฟ": "wifi", "วายฟาย": "wifi", "wi-fi": "wifi",
    "เนต": "เน็ต", "อินเตอร์เน็ต": "อินเทอร์เน็ต", "อินเตอร์เนต": "อินเทอร์เน็ต",
    "เร้าเตอร์": "เราเตอร์", "router": "เราเตอร์",
    # hardware
    "ปริ้นเตอร์": "ปริ้นเตอร์", "พริ้นเตอร์": "ปริ้นเตอร์", "ปรินเตอร์": "ปริ้นเตอร์",
    "printer": "ปริ้นเตอร์", "ปริ้น": "พิมพ์", "ปริ๊น": "พิมพ์", "พริ้น": "พิมพ์", "print": "พิมพ์",
    "คอมพิวเตอร์": "คอม", "computer": "คอม", "pc": "คอม",
    "โน๊ตบุ๊ค": "โน้ตบุ๊ก", "โน้ตบุ๊ค": "โน้ตบุ๊ก", "notebook": "โน้ตบุ๊ก", "laptop": "โน้ตบุ๊ก",
    "เม้าส์": "เมาส์", "mouse": "เมาส์", "keyboard": "คีย์บอร์ด",
    # software
    "พาสเวิร์ด": "รหัสผ่าน", "พาสเวิด": "รหัสผ่าน", "password": "รหัสผ่าน", "พาส": "รหัสผ่าน",
    "รีเซ็ท": "รีเซ็ต", "reset": "รีเซ็ต",
    "ล็อคอิน": "ล็อกอิน", "login": "ล็อกอิน",
    "แอพ": "แอป", "app": "แอป", "เมล": "อีเมล", "email": "อีเมล", "e-mail": "อีเมล",
}

REPEAT_RE = re.compile(r"([\u0E00-\u0E7Fa-zA-Z])\1{2,}")  # มากกกก -> มาก


def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("ๆ", " ")
    text = REPEAT_RE.sub(r"\1", text)
    return text


def normalize_token(token: str) -> str:
    return SYNONYMS.get(token, token)


# ---------------------------------------------------------------------------
# 3) Tokenization + Stopwords
# ---------------------------------------------------------------------------
# คำศัพท์ IT ที่ต้องการให้ตัดเป็นคำเดียว
CUSTOM_WORDS = {
    "wifi", "ไวไฟ", "vpn", "lan", "สายแลน", "เราเตอร์", "เร้าเตอร์",
    "ปริ้นเตอร์", "พริ้นเตอร์", "ปรินเตอร์", "ปริ้น", "ปริ๊น", "พริ้น",
    "รหัสผ่าน", "พาสเวิร์ด", "พาสเวิด", "รีเซ็ต", "รีเซ็ท", "ล็อกอิน", "ล็อคอิน",
    "คีย์บอร์ด", "โน้ตบุ๊ก", "โน๊ตบุ๊ค", "เมาส์", "เม้าส์", "จอฟ้า", "จอดำ",
    "เซิร์ฟเวอร์", "เน็ต", "เนต", "แอป", "แอพ", "outlook", "excel",
}
# คำที่พจนานุกรมรวมไว้เป็นคำเดียว แต่เราต้องการให้แยก
SPLIT_WORDS = {"สัญญาณไฟ", "รับสัญญาณ", "กล่องรับสัญญาณ", "ครับผม", "ค่ะผม", "คือว่า", "เน็ตช้า", "ไฟไม่เข้า"}


@lru_cache(maxsize=1)
def get_trie():
    words = (set(thai_words()) | CUSTOM_WORDS) - SPLIT_WORDS
    return dict_trie(words)


# thai_stopwords() ของ PyThaiNLP มีคำที่สำคัญกับงานนี้ปนอยู่ จึงต้องเอาออก
KEEP_WORDS = {"รับ", "เข้า", "เปิด", "ปิด", "ออก", "ช้า", "บ่อย", "ดับ", "ติด", "ใช้"}
EXTRA_STOPWORDS = {
    "ครับ", "ครับผม", "ค่ะ", "คะ", "คับ", "ค้าบ", "จ้า", "นะ", "นะคะ", "นะครับ",
    "คือ", "คือว่า", "ว่า", "ผม", "หนู", "ดิฉัน", "เรา", "พี่", "น้อง",
    "หน่อย", "ด้วย", "เลย", "มาก", "จัง", "อะ", "อ่ะ", "ช่วย", "รบกวน", "ขอบคุณ",
    "ไม่", "ได้",
}


@lru_cache(maxsize=1)
def get_stopwords() -> frozenset:
    return frozenset((set(thai_stopwords()) - KEEP_WORDS) | EXTRA_STOPWORDS)


def tokenize(text: str) -> list[str]:
    tokens = word_tokenize(text, engine="newmm", custom_dict=get_trie(), keep_whitespace=False)
    return [normalize_token(t.strip()) for t in tokens if t.strip()]


def process_tokens(text: str) -> list[str]:
    """ตัดคำ + normalize + ลบ stopwords, ตัวเลขเดี่ยว และตัวอักษรเดี่ยว"""
    stops = get_stopwords()
    result = []
    for t in tokenize(text):
        if t in stops or t.isdigit() or len(t) == 1:
            continue
        result.append(t)
    return result


# ---------------------------------------------------------------------------
# 4) Topic Identification (keyword scoring + sub-category)
#    words   = คำเดี่ยว เทียบกับ token (1 คะแนน)
#    phrases = regex เทียบกับข้อความเต็มที่ตัดช่องว่างแล้ว (2 คะแนน)
#    ใช้ข้อความก่อนลบ stopword เพื่อจับวลีอย่าง "เข้าเว็บไม่ได้" ได้
# ---------------------------------------------------------------------------
CATEGORIES = {
    "Network": {
        "team": "Network Engineer Team",
        "subcategories": {
            "Wi-Fi หลุด / สัญญาณอ่อน": {
                "words": ["wifi", "สัญญาณ", "หลุด", "แอคเซสพอยต์", "ap"],
                "phrases": [r"wifi.{0,10}(หลุด|อ่อน|ไม่มี|ช้า)", r"สัญญาณ.{0,5}(อ่อน|หลุด|ไม่มี)"],
            },
            "LAN สาย / พอร์ตเสีย": {
                "words": ["lan", "สายแลน", "แลน", "พอร์ต", "สวิตช์"],
                "phrases": [r"สาย(แลน|lan).{0,10}(เสีย|ขาด|หลวม)"],
            },
            "VPN เชื่อมต่อไม่ได้": {
                "words": ["vpn"],
                "phrases": [r"vpn.{0,10}(ไม่ได้|หลุด)"],
            },
            "อินเทอร์เน็ตช้า / เข้าเว็บไม่ได้": {
                "words": ["เน็ต", "อินเทอร์เน็ต", "เว็บ", "เว็บไซต์", "เราเตอร์", "dns", "ip", "เชื่อมต่อ", "ช้า"],
                "phrases": [r"เน็ต.{0,6}(ช้า|หลุด|ไม่ได้|ล่ม)", r"เข้า(เว็บ|เน็ต).{0,6}ไม่ได้",
                            r"เชื่อมต่อ.{0,6}ไม่ได้"],
            },
        },
    },
    "Hardware": {
        "team": "Hardware Technician Team",
        "subcategories": {
            "เครื่องเปิดไม่ติด / ไฟไม่เข้า": {
                "words": ["คอม", "เครื่อง", "โน้ตบุ๊ก", "ไฟ", "ดับ", "ปลั๊ก", "อะแดปเตอร์", "แบตเตอรี่"],
                "phrases": [r"เปิด.{0,15}ไม่ติด", r"ไฟ.{0,4}ไม่เข้า", r"(คอม|เครื่อง).{0,6}ดับ", r"จอ(ฟ้า|ดำ)"],
            },
            "ปริ้นเตอร์": {
                "words": ["ปริ้นเตอร์", "พิมพ์", "หมึก", "กระดาษ", "สแกนเนอร์"],
                "phrases": [r"(พิมพ์|ปริ้น).{0,8}ไม่ออก", r"กระดาษ.{0,3}ติด", r"หมึก.{0,3}หมด"],
            },
            "อุปกรณ์ต่อพ่วง": {
                "words": ["จอ", "เมาส์", "คีย์บอร์ด", "ลำโพง", "หูฟัง", "usb", "โปรเจคเตอร์", "กล้อง"],
                "phrases": [r"(เมาส์|คีย์บอร์ด).{0,6}(ค้าง|ไม่ติด|เสีย)", r"จอ.{0,6}(ไม่ติด|กระพริบ|เป็นเส้น)"],
            },
        },
    },
    "Software": {
        "team": "Software Support Team",
        "subcategories": {
            "บัญชี / รหัสผ่าน": {
                "words": ["รหัสผ่าน", "รหัส", "ล็อกอิน", "รีเซ็ต", "ยูสเซอร์", "สิทธิ์"],
                "phrases": [r"ลืมรหัส", r"เข้าระบบ.{0,4}ไม่ได้", r"(ล็อกอิน|login).{0,6}ไม่ได้",
                            r"ขอสิทธิ์", r"บัญชี.{0,6}(ล็อก|ถูกระงับ|เข้าไม่ได้|หมดอายุ)"],
            },
            "โปรแกรม / แอปพลิเคชัน": {
                "words": ["โปรแกรม", "แอป", "ติดตั้ง", "อัปเดต", "error", "excel", "word", "windows",
                          "ไวรัส", "ไลเซนส์", "เด้ง"],
                "phrases": [r"(โปรแกรม|แอป).{0,10}(ไม่ได้|ค้าง|เด้ง|error)", r"เปิดโปรแกรม"],
            },
            "อีเมล": {
                "words": ["อีเมล", "outlook", "gmail"],
                "phrases": [r"อีเมล.{0,8}(ส่ง|รับ).{0,4}(ไม่ได้|ไม่ออก|ไม่เข้า)"],
            },
        },
    },
}

FALLBACK_CATEGORY = "General Support"
FALLBACK_TEAM = "Frontline Helpdesk"
CONFIDENCE_THRESHOLD = 0.60  # ต่ำกว่านี้ส่งเข้าคิว Human Review

ALL_TEAMS = [c["team"] for c in CATEGORIES.values()] + [FALLBACK_TEAM]
TEAM_TO_CATEGORY = {c["team"]: name for name, c in CATEGORIES.items()}
TEAM_TO_CATEGORY[FALLBACK_TEAM] = FALLBACK_CATEGORY


def classify_topic(tokens: list[str], full_text: str) -> dict:
    """ให้คะแนนแต่ละหมวดจากคำเดี่ยวและวลี แล้วเลือกหมวดที่คะแนนสูงสุด"""
    compact = full_text.replace(" ", "")
    token_set = set(tokens)

    cat_scores, sub_scores, matched = {}, {}, {}
    for cat, cfg in CATEGORIES.items():
        cat_total = 0
        for sub, rules in cfg["subcategories"].items():
            hits = [w for w in rules["words"] if w in token_set]
            phrase_hits = [m.group(0) for p in rules["phrases"] if (m := re.search(p, compact))]
            score = len(hits) + 2 * len(phrase_hits)
            sub_scores[(cat, sub)] = score
            if hits or phrase_hits:
                matched.setdefault(cat, []).extend(hits + phrase_hits)
            cat_total += score
        cat_scores[cat] = cat_total

    total = sum(cat_scores.values())
    ranked = sorted(cat_scores.items(), key=lambda kv: kv[1], reverse=True)
    best, best_score = ranked[0]
    is_tie = len(ranked) > 1 and ranked[1][1] == best_score

    if total == 0:
        return {
            "category": FALLBACK_CATEGORY, "subcategory": "-", "team": FALLBACK_TEAM,
            "confidence": 0.0, "scores": cat_scores, "matched": [],
            "needs_review": True, "review_reason": "ไม่พบคำที่บ่งบอกหมวดหมู่",
        }

    confidence = best_score / total
    subcategory = max(
        (s for (c, s) in sub_scores if c == best), key=lambda s: sub_scores[(best, s)]
    )
    needs_review, reason = False, ""
    if is_tie:
        needs_review, reason = True, f"คะแนนเท่ากันระหว่าง {best} และ {ranked[1][0]}"
    elif confidence < CONFIDENCE_THRESHOLD:
        needs_review, reason = True, f"ความมั่นใจต่ำกว่า {int(CONFIDENCE_THRESHOLD * 100)}%"

    return {
        "category": best, "subcategory": subcategory, "team": CATEGORIES[best]["team"],
        "confidence": round(confidence, 2), "scores": cat_scores,
        "matched": sorted(set(matched.get(best, []))),
        "needs_review": needs_review, "review_reason": reason,
    }


# ---------------------------------------------------------------------------
# 5) Priority Detection
# ---------------------------------------------------------------------------
HIGH_PATTERNS = [r"ด่วน", r"ทั้ง(ชั้น|ตึก|แผนก|ฝ่าย|บริษัท|ออฟฟิศ)", r"ทุกคน", r"ทุกเครื่อง", r"ล่ม",
                 r"ใช้(งาน)?ไม่ได้เลย", r"ประชุม", r"ลูกค้า", r"เซิร์ฟเวอร์", r"server", r"ไวรัส",
                 r"ข้อมูลหาย", r"ไฟไหม้|ควัน"]
LOW_PATTERNS = [r"ลืมรหัส", r"สอบถาม", r"ขอ(ติดตั้ง|สิทธิ์|คำแนะนำ)", r"ไม่รีบ", r"เมื่อสะดวก",
                r"หมึก.{0,3}หมด"]


def detect_priority(full_text: str) -> tuple[str, list[str]]:
    compact = full_text.replace(" ", "").lower()
    high = [m.group(0) for p in HIGH_PATTERNS if (m := re.search(p, compact))]
    if high:
        return "High", high
    low = [m.group(0) for p in LOW_PATTERNS if (m := re.search(p, compact))]
    if low:
        return "Low", low
    return "Medium", []


# ---------------------------------------------------------------------------
# 6) NER (rule-based: dictionary + regex) และ POS Tagging
# ---------------------------------------------------------------------------
DEVICES = ["ปริ้นเตอร์", "คอม", "โน้ตบุ๊ก", "จอ", "เมาส์", "คีย์บอร์ด", "เราเตอร์", "สวิตช์",
           "โปรเจคเตอร์", "สแกนเนอร์", "ลำโพง", "หูฟัง", "กล่องรับสัญญาณ", "สายแลน", "wifi",
           "เซิร์ฟเวอร์", "โทรศัพท์", "แท็บเล็ต", "usb"]

LOCATION_RE = re.compile(
    r"(ห้อง|ตึก|อาคาร|ชั้น|โซน|room|building|floor)\s*([A-Za-z]{0,3}\d+[A-Za-z0-9\-/.]*|[A-Za-z]{1,3})",
    re.IGNORECASE,
)
DEPARTMENT_RE = re.compile(r"(?<!ทั้ง)(แผนก|ฝ่าย)\s*([\u0E00-\u0E7FA-Za-z]+)")
# ชื่อเรียกอุปกรณ์แบบอื่นที่ต้องแปลงเป็นชื่อมาตรฐาน
DEVICE_ALIASES = {"เครื่องปริ้น": "ปริ้นเตอร์", "เครื่องพิมพ์": "ปริ้นเตอร์"}

TIME_WORDS = ["เมื่อเช้า", "เช้านี้", "เมื่อวาน", "เมื่อคืน", "เมื่อกี้", "บ่ายนี้", "เย็นนี้", "วันนี้",
              "ตอนนี้", "สัปดาห์ที่แล้ว", "อาทิตย์ที่แล้ว", "เดือนที่แล้ว", "ทั้งวัน", "เมื่อวันจันทร์",
              "เมื่อวันอังคาร", "เมื่อวันพุธ", "เมื่อวันพฤหัส", "เมื่อวันศุกร์"]
CLOCK_RE = re.compile(r"\d{1,2}[:.]\d{2}\s*(น\.|นาฬิกา)?|\d{1,2}\s*โมง(เช้า|เย็น)?|บ่าย\s*\d\s*โมง")


def extract_entities(text_no_pii: str) -> dict:
    """สกัด DEVICE, LOCATION, TIME จากข้อความที่ลบข้อมูลส่วนตัวแล้ว (ยังมีเครื่องหมาย เช่น B4-01A)"""
    norm = normalize_text(text_no_pii)
    norm_tokens = set(tokenize(clean_text(norm)))

    compact = norm.replace(" ", "")
    devices = [d for d in DEVICES if d in norm_tokens or (len(d) > 3 and d in compact)]
    devices += [canon for alias, canon in DEVICE_ALIASES.items() if alias in compact]
    devices = list(dict.fromkeys(devices))

    locations = [f"{m.group(1)} {m.group(2)}".strip() for m in LOCATION_RE.finditer(text_no_pii)]
    for m in DEPARTMENT_RE.finditer(text_no_pii):
        # ใช้การตัดคำเพื่อเอาเฉพาะคำแรกหลัง "แผนก" เช่น "แผนกบัญชีด่วน" -> "แผนกบัญชี"
        first = word_tokenize(m.group(2), engine="newmm", custom_dict=get_trie())[0]
        if first not in get_stopwords():
            locations.append(f"{m.group(1)}{first}")

    times = [w for w in TIME_WORDS if w in compact]
    times += [m.group(0).strip() for m in CLOCK_RE.finditer(text_no_pii)]
    since = re.search(r"ตั้งแต่\s*([\u0E00-\u0E7F0-9:.]+)", text_no_pii)
    if since and not times:
        times.append(since.group(0))

    return {
        "DEVICE": devices,
        "LOCATION": list(dict.fromkeys(locations)),
        "TIME": list(dict.fromkeys(times)),
    }


def extract_keywords_pos(tokens: list[str]) -> list[tuple[str, str]]:
    """ใช้ POS Tagging เลือกเฉพาะคำนามและคำกริยาเป็นคำสำคัญของตั๋ว"""
    try:
        from pythainlp.tag import pos_tag
        tagged = pos_tag(tokens, corpus="orchid_ud")
    except Exception:
        return [(t, "-") for t in tokens]
    return [(w, tag) for w, tag in tagged if tag in {"NOUN", "PROPN", "VERB"}]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def analyze_ticket(raw_text: str) -> dict:
    no_pii, removed = remove_pii(raw_text)
    entities = extract_entities(no_pii)
    cleaned = clean_text(normalize_text(no_pii))
    tokens = process_tokens(cleaned)
    # ข้อความที่แปลงคำสะกดหลายแบบเป็นคำมาตรฐานแล้ว (ยังไม่ลบ stopword) ใช้จับวลี
    normalized_full = "".join(tokenize(cleaned))
    topic = classify_topic(tokens, normalized_full)
    priority, priority_hits = detect_priority(normalized_full)
    keywords = extract_keywords_pos(tokens)

    return {
        "raw_text": raw_text,
        "removed_pii": removed,
        "cleaned_text": cleaned,
        "tokens": tokens,
        **topic,
        "priority": priority,
        "priority_hits": priority_hits,
        "entities": entities,
        "pos_keywords": keywords,
    }
