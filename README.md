# 📱 Mobile Legends: Bang Bang (MLBB) Telegram News AI Agent

> **AI-powered avtomatlashtirilgan Telegram yangiliklar agenti**: MLBB rasmiy yangiliklari, Patch Notes, Hero buff/nerf/adjustments, yangi skinlar, tadbirlar, **MPL Indonesia (MPL ID)** va **MPL Philippines (MPL PH)** o‘yin jadvallari hamda natijalarini to‘playdi, AI yordamida o‘zbek tilida professional postga aylantiradi va Telegram kanalga joylaydi.

---

## 🚀 Asosiy Imkoniyatlar

1. **Rasmiy Manbalar Bilan Ishlash (Source Priority):**
   - MLBB Rasmiy sayti va Patch Notes sahifalari (Prioritet: 100).
   - MPL ID (`https://id-mpl.com/schedule` va `news`).
   - MPL PH (`https://ph-mpl.com/schedule`).
   - Global Esports (M-Series, MSC, ESL Snapdragon).
2. **AI Analyzer & Hallucination Protection ("NO SOURCE = NO CLAIM"):**
   - Manbada mavjud bo‘lmagan narx, hisob, o‘yinchi yoki sana kabi ma’lumotlarni o‘ylab topish qat'iy taqiqlangan.
   - OpenAI (GPT-4o-mini / OpenAI-compatible / Gemini / OpenRouter) orqali professional o‘zbekcha post yaratish.
   - API kalit kiritilmagan bo‘lsa ham, deterministic NLP parser orqali to‘liq ishlaydi.
3. **Admin Approval Mode & Auto Mode:**
   - **Approval Mode (MVP tavsiya etiladi)**: Yangilik avval adminga `[✅ Publish] [❌ Reject] [✏️ Edit]` tugmalari bilan yuboriladi.
   - **Auto Mode**: To‘g‘ridan-to‘g‘ri kanalga avtomatik joylash.
4. **Takroriy Xabarlardan Himoya (Duplicate Protection):**
   - SHA-256 `content_hash` va kanonik URL orqali avval yuborilgan yangiliklarni qayta yubormaslik.
5. **Media va Grafikalar Generatsiyasi (Image Processor):**
   - Patch Notes uchun yashil BUFF va qizil NERF grafik bannerlari (Pillow).
   - MPL Matchup va natija kartalari.
   - Manba rasmlarini avtomatik yuklab olish va Telegram formatiga optimallashtirish.
6. **Graceful Error Handling (Resilient Pipeline):**
   - Agar biron manba ishlamay qolsa, butun tizim to‘xtab qolmaydi.
   - Adminga alert xabarnomasi yuboriladi va boshqa manbalar bilan ishlash davom etadi.

---

## 🏛 Arxitektura (Data Flow)

```
        INTERNET
           │
           ▼
 ┌────────────────────┐
 │ OFFICIAL SOURCES   │  MLBB Official / MPL ID / MPL PH / Esports
 └─────────┬──────────┘
           │
           ▼
 ┌────────────────────┐
 │     COLLECTOR      │  Web Scraping / HTTPX / HTML & JSON Parsing
 └─────────┬──────────┘
           │
           ▼
 ┌────────────────────┐
 │    NORMALIZER      │  Structured Pydantic Models & Content Hashes
 └─────────┬──────────┘
           │
           ▼
 ┌────────────────────┐
 │    AI ANALYZER     │  Classify + Summarize + Translate (Uzbek)
 └─────────┬──────────┘
           │
           ▼
 ┌────────────────────┐
 │    VERIFICATION    │  "NO SOURCE = NO CLAIM", Reliability & Duplicate Check
 └─────────┬──────────┘
           │
           ▼
 ┌────────────────────┐
 │   POST GENERATOR   │  Templates + Pillow Graphic Overlay
 └─────────┬──────────┘
           │
           ▼
 ┌────────────────────┐
 │ TELEGRAM BOT API   │  Aiogram 3.x (Admin Approval / Auto Publish)
 └─────────┬──────────┘
           │
           ▼
 ┌────────────────────┐
 │   TELEGRAM KANAL   │
 └────────────────────┘
```

---

## 📂 Loyiha Strukturasi

```
mlbb-news-agent/
│
├── app/
│   ├── main.py                     # Dasturni ishga tushirish (Entry point)
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py             # Pydantic-settings konfiguratsiyasi
│   │
│   ├── collectors/                 # Modulli ma'lumot yig'uvchilar
│   │   ├── __init__.py
│   │   ├── base.py                 # SourceCollector abstrakt klassi
│   │   ├── mlbb_official.py        # MLBB rasmiy yangiliklar va patch notes
│   │   ├── mpl_id.py               # MPL Indonesia jadvali va natijalari
│   │   ├── mpl_ph.py               # MPL Philippines jadvali va natijalari
│   │   └── esports.py              # Global turnirlar (M6, ESL)
│   │
│   ├── ai/                         # AI tahlil va tarjima moduli
│   │   ├── __init__.py
│   │   ├── analyzer.py             # AI Analyzer (OpenAI + NLP fallback)
│   │   ├── summarizer.py           # Matnni qisqartirish va muhim qismlar
│   │   ├── translator.py           # MLBB o'zbek tili lokalizatsiyasi
│   │   └── formatter.py            # Section 8 bo'yicha post shablonlari
│   │
│   ├── database/                   # Ma'lumotlar bazasi (SQLAlchemy Async)
│   │   ├── __init__.py
│   │   ├── models.py               # Post, Match, Source, SystemLog modellari
│   │   ├── database.py             # Async Engine va Session yaratuvchi
│   │   └── repositories.py         # CRUD va Duplicate tekshiruvlari
│   │
│   ├── telegram/                   # Telegram bot va nashriyot
│   │   ├── __init__.py
│   │   ├── bot.py                  # Aiogram 3.x bot komandalari (/status, /test, /send)
│   │   ├── publisher.py            # Kanalga nashr qilish
│   │   └── admin.py                # Admin Approval Mode (Inline keyboard)
│   │
│   ├── scheduler/                  # Avtomatik davriy ishlar (APScheduler)
│   │   ├── __init__.py
│   │   └── jobs.py                 # 10m/15m/1h intervaldagi pipeline
│   │
│   ├── media/                      # Rasm va grafika yaratish
│   │   ├── __init__.py
│   │   └── image_processor.py      # Pillow asosida Patch & Matchup bannerlari
│   │
│   └── utils/
│       ├── __init__.py
│       ├── hashing.py              # SHA-256 deduplication
│       ├── logger.py               # Structured logging
│       └── validators.py           # Pydantic validatsiyasi & No claim qoidasi
│
├── tests/                          # To'liq testlar to'plami (Pytest)
│   ├── test_ai_analyzer.py
│   ├── test_collectors.py
│   ├── test_database.py
│   ├── test_hashing.py
│   ├── test_image_processor.py
│   ├── test_scheduler_pipeline.py
│   ├── test_telegram_bot.py
│   └── test_validators.py
│
├── .env.example                    # Muhit o'zgaruvchilari namunasi
├── requirements.txt                # Python kutubxonalari
├── Dockerfile                      # Docker container
├── docker-compose.yml              # Docker Compose servislari
└── pytest.ini                      # Pytest konfiguratsiyasi
```

---

## ⚙️ O‘rnatish va Ishga Tushirish

### 1. Lokal Muhit (Python 3.12+)

```bash
# Repozitoriyga kiring
cd "Solo mlbb ai agent"

# Virtual muhit yarating va faollashtiring
python3 -m venv .venv
source .venv/bin/activate

# Bog'liqliklarni o'rnating
pip install -r requirements.txt
```

### 2. `.env` Faylini Sozlash

`.env.example` nusxasini `.env` nomi bilan yarating va qiymatlarni kiriting:

```env
TELEGRAM_BOT_TOKEN=1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHANNEL_ID=@mlbb_news_uz
ADMIN_TELEGRAM_ID=123456789

# AI sozlamalari
AI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini

# Ma'lumotlar bazasi
DATABASE_URL=sqlite+aiosqlite:///./mlbb_news.db

# Rejim: false = Admin tasdiqlashi (Tavsiya etiladi), true = To'g'ridan-to'g'ri kanalga chiqarish
AUTO_PUBLISH=false
```

### 3. Agentni Ishga Tushirish

```bash
python -m app.main
```

---

## 🐳 Docker Orqali Ishga Tushirish

```bash
# Docker Compose orqali containerlarni yig'ish va ishga tushirish
docker-compose up -d --build

# Loglarni kuzatish
docker-compose logs -f mlbb-agent
```

---

## 🤖 Telegram Bot Buyruqlari

| Buyruq | Kim uchun | Vazifasi |
| :--- | :--- | :--- |
| `/start`, `/help` | Barcha | Bot haqida ma'lumot |
| `/status` | Barcha / Admin | Tizim holati (Onlayn, oxirgi tekshiruvlar, xatolar soni) |
| `/latest` | Barcha | Bazadagi so‘nggi 5 ta yangilik holati |
| `/test` | Admin | Manbalardan test olinmasini tekshirish va ko‘rsatish |
| `/send <id>` | Admin | Postni kanalga majburiy yuborish |
| `/pause` | Admin | Scheduler yangilik yig‘ishni vaqtincha to‘xtatish |
| `/resume` | Admin | Scheduler yangilik yig‘ishni qayta davom ettirish |

---

## 🧪 Testlarni Ishga Tushirish

Barcha 21 ta unit va integratsion testlarni tekshirish:

```bash
source .venv/bin/activate
pytest -v
```

Natija:
```
============================= 21 passed in 12.50s ==============================
```

---

## 🛠 Yangi Manba (Source) Qo'shish

Clean Architecture tufayli yangi manba qo'shish juda oddiy. `SourceCollector` dan meros oling:

```python
from app.collectors.base import SourceCollector
from app.utils.validators import RawCollectedItem, CategoryEnum

class CustomSourceCollector(SourceCollector):
    def __init__(self):
        super().__init__(
            name="Custom Source",
            source_type="COMMUNITY",
            base_url="https://custom-mlbb-source.com",
            reliability_score=60
        )

    async def fetch(self) -> list[RawCollectedItem]:
        resp = await self._get(f"{self.base_url}/news")
        # Parsing mantiqi...
        return []
```
Keyin `app/scheduler/jobs.py` ichiga yangi kollektorni ro'yxatdan o'tkazasiz.
