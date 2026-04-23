# 📍 GPS Checkpoint Verification Bot

Telegram bot for worker checkpoint verification based on GPS location.

Workers go to different job sites/objects. They must press a checkpoint button in the bot, select the object they arrived at, and send their current location. The bot verifies whether the worker is within 500 meters of the selected object.

## 🏗 Architecture

```
checkpoint_bot/
├── bot/
│   ├── main.py                    # Entry point
│   ├── config.py                  # Settings (.env)
│   ├── handlers/                  # Telegram handlers
│   │   ├── start.py               # /start, main menu
│   │   ├── checkpoint.py          # Checkpoint flow (FSM)
│   │   ├── history.py             # User history
│   │   ├── objects_list.py        # Objects list
│   │   ├── help.py                # Help & contact
│   │   ├── settings.py            # User settings
│   │   └── admin.py               # Admin CRUD
│   ├── services/                  # Business logic
│   │   ├── checkpoint_service.py  # Verification + CRUD
│   │   ├── notification_service.py # Admin notifications
│   │   └── user_service.py        # User management
│   ├── models/
│   │   └── models.py              # SQLAlchemy ORM
│   ├── database/
│   │   └── db.py                  # DB engine & session
│   ├── keyboards/                 # Telegram keyboards
│   │   ├── user_kb.py             # User keyboards
│   │   └── admin_kb.py            # Admin keyboards
│   ├── states/
│   │   └── states.py              # FSM states
│   ├── middlewares/
│   │   └── db_middleware.py       # DB session injection
│   └── utils/
│       └── haversine.py           # Distance calculation
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## ⚡ Quick Start

### 1. Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

### 2. Setup

```bash
# Papkaga kirish
cd checkpoint_bot

# Virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Dependencies
pip install -r requirements.txt

# .env faylini yaratish
cp .env.example .env
# .env faylini tahrirlang: BOT_TOKEN, DATABASE_URL, ADMIN_TELEGRAM_ID
```

### 3. Database

```bash
# PostgreSQL da database yaratish
createdb checkpoint_bot

# Yoki psql orqali
psql -U postgres -c "CREATE DATABASE checkpoint_bot;"
```

### 4. Run

```bash
# Botni ishga tushirish
python -m bot.main
```

## 🐳 Docker bilan ishga tushirish

```bash
# .env faylini sozlang
cp .env.example .env
nano .env  # BOT_TOKEN va ADMIN_TELEGRAM_ID ni kiriting

# Docker bilan ishga tushirish
docker-compose up -d --build

# Loglarni ko'rish
docker-compose logs -f bot
```

## 🔧 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram Bot API Token | — (required) |
| `DATABASE_URL` | PostgreSQL connection URL | localhost:5432/checkpoint_bot |
| `ADMIN_TELEGRAM_ID` | Admin's Telegram user ID | 0 |
| `DEFAULT_RADIUS` | Default checkpoint radius (m) | 500 |

### Admin Telegram ID ni qanday bilish?

1. [@userinfobot](https://t.me/userinfobot) ga `/start` yuboring
2. Bot sizning Telegram ID'ingizni ko'rsatadi
3. Shu raqamni `.env` fayliga `ADMIN_TELEGRAM_ID` ga yozing

## 📱 Bot menyu

### Ishchi menyu:
- 📍 **Checkpoint qilish** — Kelganingizni tasdiqlash
- 📋 **Mening tarixim** — Checkpoint tarixingiz
- 🏗 **Obyektlar ro'yxati** — Barcha ish joylari
- ❓ **Yordam** — Foydalanish ko'rsatmasi
- 📞 **Admin bilan aloqa** — Adminga yozish
- ⚙️ **Sozlamalar** — Profil ma'lumotlari

### Admin menyu (qo'shimcha):
- 🔧 **Admin panel** →
  - ➕ Obyekt qo'shish
  - ✏️ Obyektni tahrirlash
  - 🗑 Obyektni o'chirish
  - 📋 Barcha obyektlar
  - 📊 Checkpoint tarixlari

## 📐 Masofa hisoblash

**Haversine formulasi** ishlatiladi:

```
a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
c = 2 × atan2(√a, √(1−a))
d = R × c   (R = 6,371,000 m)
```

Default threshold: **500 metr**

## 📊 Database Schema

### users
- `id`, `telegram_id`, `username`, `first_name`, `last_name`
- `phone`, `language`, `is_admin`, `created_at`, `updated_at`

### objects
- `id`, `name`, `latitude`, `longitude`, `radius`
- `address`, `is_active`, `created_at`, `updated_at`

### checkpoints
- `id`, `user_id` → users, `object_id` → objects
- `user_latitude`, `user_longitude`, `distance_meters`
- `status` (accepted/rejected), `created_at`

## 🚀 Deploy (Railway / Render)

1. GitHub ga push qiling
2. Railway/Render da yangi project yarating
3. Environment variables sozlang
4. PostgreSQL plugin qo'shing
5. Deploy!

### Railway

```bash
# railway.json (root directory: checkpoint_bot)
{
  "build": {"builder": "DOCKERFILE"},
  "deploy": {"startCommand": "python -m bot.main"}
}
```

## 📝 License

MIT
