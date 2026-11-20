"""
Jarima tizimi testlari — soxta Supabase va soxta bot bilan.
Ishga tushirish: python -m tests.test_fines
"""

import asyncio
import copy
import os
from datetime import date, datetime, timedelta

os.environ.setdefault("SUPABASE_URL", "http://fake")
os.environ.setdefault("SUPABASE_KEY", "fake")
os.environ["ADMIN_IDS"] = "111"
os.environ["CHANNEL_ID"] = "-100"

from bot.database import db  # noqa: E402
from bot.services import fine_scheduler as fs  # noqa: E402
from bot.services.fine_service import TASHKENT, current_period, due_periods  # noqa: E402

PK = {"bot_settings": "key", "bot_users": "user_id"}


class Result:
    def __init__(self, data):
        self.data = data
        self.count = len(data)


class Query:
    def __init__(self, store, table):
        self.store, self.table = store, table
        self.rows = store.setdefault(table, [])
        self.filters, self.op, self.payload = [], "select", None
        self._order, self._limit = None, None

    def select(self, *a, **k): self.op = "select"; return self
    def insert(self, payload): self.op, self.payload = "insert", payload; return self
    def update(self, payload): self.op, self.payload = "update", payload; return self
    def upsert(self, payload): self.op, self.payload = "upsert", payload; return self
    def eq(self, c, v): self.filters.append(lambda r: r.get(c) == v); return self
    def gte(self, c, v): self.filters.append(lambda r: r.get(c) is not None and r[c] >= v); return self
    def lte(self, c, v): self.filters.append(lambda r: r.get(c) is not None and r[c] <= v); return self
    def lt(self, c, v): self.filters.append(lambda r: r.get(c) is not None and r[c] < v); return self
    def order(self, c, desc=False): self._order = (c, desc); return self
    def limit(self, n): self._limit = n; return self

    def execute(self):
        if self.op == "insert":
            row = dict(self.payload)
            row.setdefault("id", len(self.rows) + 1)
            if self.table == "fines":
                row.setdefault("status", "active")
                row.setdefault("reported", False)
                assert not any(
                    r["object_id"] == row["object_id"] and r["period_start"] == row["period_start"] for r in self.rows
                ), "unique violation"
            self.rows.append(row)
            return Result([copy.deepcopy(row)])
        if self.op == "upsert":
            pk = PK[self.table]
            for r in self.rows:
                if r[pk] == self.payload[pk]:
                    r.update(self.payload)
                    return Result([r])
            self.rows.append(dict(self.payload))
            return Result([self.payload])
        matched = [r for r in self.rows if all(f(r) for f in self.filters)]
        if self.op == "update":
            for r in matched:
                r.update(self.payload)
            return Result(matched)
        if self._order:
            matched.sort(key=lambda r: r.get(self._order[0]) or "", reverse=self._order[1])
        if self._limit:
            matched = matched[: self._limit]
        return Result(copy.deepcopy(matched))


class FakeSupabase:
    def __init__(self): self.store = {}
    def table(self, name): return Query(self.store, name)


class FakeBot:
    def __init__(self): self.sent = []
    async def send_message(self, chat_id, text, **kw): self.sent.append((chat_id, text, kw))
    def to(self, chat_id): return [t for c, t, _ in self.sent if c == chat_id]


def at(d: date, hour=10):
    return datetime(d.year, d.month, d.day, hour, tzinfo=TASHKENT)


def cp(sb, uid, name, obj, when: datetime, status="Keldi"):
    sb.table("checkpoints").insert({
        "user_id": uid, "username": name, "object_name": obj, "status": status,
        "created_at": when.astimezone(fs.timezone.utc).isoformat(),
    }).execute()


def test_periods():
    L = date(2026, 11, 20)
    # eski obyekt: hisob ishga tushgan kundan boshlanadi
    assert due_periods(date(2026, 9, 1), L, None, date(2026, 11, 26), 7) == []
    assert due_periods(date(2026, 9, 1), L, None, date(2026, 11, 27), 7) == [(L, date(2026, 11, 27))]
    # yangi obyekt: o'z sanasidan
    S = date(2026, 11, 25)
    assert due_periods(S, L, None, date(2026, 12, 9), 7) == [
        (S, date(2026, 12, 2)), (date(2026, 12, 2), date(2026, 12, 9))]
    assert due_periods(S, L, date(2026, 12, 2), date(2026, 12, 9), 7) == [(date(2026, 12, 2), date(2026, 12, 9))]
    assert current_period(S, L, date(2026, 11, 24), 7) is None
    assert current_period(S, L, date(2026, 12, 3), 7) == (date(2026, 12, 2), date(2026, 12, 9))


async def scenario():
    sb = FakeSupabase()
    db._supabase = sb
    bot = FakeBot()
    admin = fs.settings.FINE_ADMIN_ID
    L = date(2026, 11, 20)

    sb.table("objects").insert({"name": "A", "created_at": "2026-09-01T00:00:00+00:00", "start_date": None,
                                "start_asked_at": None, "fine_checked_until": None, "fine_warned_period": None}).execute()
    sb.table("objects").insert({"name": "B", "created_at": "2026-09-01T00:00:00+00:00", "start_date": None,
                                "start_asked_at": None, "fine_checked_until": None, "fine_warned_period": None}).execute()
    sb.table("objects").insert({"name": "C", "start_date": None, "start_asked_at": None,
                                "fine_checked_until": None, "fine_warned_period": None}).execute()
    cp(sb, 501, "@ali", "A", at(date(2026, 11, 10)))
    cp(sb, 502, "@vali", "B", at(date(2026, 11, 11)))
    for t in ("fines", "bot_settings", "bot_users"):
        sb.store.setdefault(t, [])

    # Tunda hech narsa yuborilmaydi
    await fs.tick(bot, at(L, 3))
    assert bot.sent == []

    # 1-kun: e'lon hammaga + admin'dan 3 ta obyekt sanasi so'raladi
    await fs.tick(bot, at(L, 11))
    assert any("Muhim e'lon" in t for t in bot.to(501)) and any("Muhim e'lon" in t for t in bot.to(502))
    assert any("Muhim e'lon" in t for t in bot.to(111)) and any("Muhim e'lon" in t for t in bot.to(-100))
    assert len([t for t in bot.to(admin) if "qaysi kundan" in t]) == 3
    n = len(bot.sent)
    await fs.tick(bot, at(L, 12))  # takror e'lon ham, takror savol ham yo'q
    assert len(bot.sent) == n

    # Admin javob beradi: A va B — eski sana, C — javobsiz
    svc = fs.FineService()
    svc.set_start_date(1, date(2026, 9, 1))
    svc.set_start_date(2, date(2026, 9, 1))

    # A da checkpoint bo'ladi, B da yo'q
    cp(sb, 501, "@ali", "A", at(date(2026, 11, 22)))
    cp(sb, 502, "@vali", "B", at(date(2026, 11, 23)), status="Kelmadi")  # rad etilgan — hisoblanmaydi

    # 6-kun (2 kun qoldi): B bo'yicha eslatma faqat @vali ga, bir marta
    bot.sent.clear()
    await fs.tick(bot, at(date(2026, 11, 25)))
    await fs.tick(bot, at(date(2026, 11, 25), 15))
    assert len([t for t in bot.to(502) if "Eslatma" in t]) == 1
    assert not [t for t in bot.to(501) if "Eslatma" in t]

    # 8-kun: B uchun jarima @vali ga, A ga yo'q; takrorlanmaydi
    bot.sent.clear()
    await fs.tick(bot, at(date(2026, 11, 27)))
    await fs.tick(bot, at(date(2026, 11, 27), 15))
    fines = sb.store["fines"]
    assert len(fines) == 1 and fines[0]["object_name"] == "B" and fines[0]["user_id"] == 502 and fines[0]["amount"] == 50
    assert len([t for t in bot.to(502) if "jarima yozildi" in t]) == 1
    assert len([t for t in bot.to(admin) if "Yangi jarima" in t]) == 1
    msg = bot.to(502)[0]
    assert "20.11–26.11.2026" in msg and "Sababi" in msg
    assert "oxirgi checkpoint: 11.11.2026" in msg and "hali borilmagan — 16 kun" in msg
    assert "Sababi" in [t for t in bot.to(admin) if "Yangi jarima" in t][0]

    # Ishchi kechikib bo'lsa ham boradi — oylik hisobotda sabab aniq ko'rinadi
    cp(sb, 502, "@vali", "B", at(date(2026, 11, 29)))

    # Oy oxiri: 18:00 dan oldin yo'q, keyin hisobot — admin(lar)ga va ishchilarga, bir marta
    bot.sent.clear()
    await fs.tick(bot, at(date(2026, 11, 30), 12))
    assert not [t for _, t, _ in bot.sent if "hisoboti" in t]
    await fs.tick(bot, at(date(2026, 11, 30), 18))
    await fs.tick(bot, at(date(2026, 11, 30), 19))
    assert len([t for t in bot.to(admin) if "Jarimalar hisoboti" in t]) == 1
    assert len([t for t in bot.to(111) if "Jarimalar hisoboti" in t]) == 1
    rep = [t for t in bot.to(admin) if "Jarimalar hisoboti" in t][0]
    assert "@vali" in rep and "Jami: 1 ta jarima, <b>50$</b>" in rep
    assert any("Jami: 1 ta jarima" in t for t in bot.to(502))
    for text in (rep, [t for t in bot.to(502) if "Jami: 1 ta jarima" in t][0]):
        assert "20.11–26.11.2026 — 7 kun ichida bir marta ham checkpoint qilinmadi" in text
        assert "oxirgi checkpoint: 11.11.2026" in text
        assert "Keyin 29.11.2026 da borilgan (@vali) — orada 18 kun o'tgan (ruxsat etilgani 7 kun)" in text
    assert any("jarima yo'q" in t for t in bot.to(501))
    assert fines[0]["reported"] is True

    # Sanasi yo'q C qayta so'ralgan (24 soatdan keyin), jarima yozilmagan
    assert all(f["object_name"] != "C" for f in fines)

    # Yangi obyekt D (hech kim checkpoint qilmagan): jarima ishchisiz, admin tanlaydi
    sb.table("objects").insert({"name": "D", "start_date": "2026-12-01", "start_asked_at": None,
                                "fine_checked_until": None, "fine_warned_period": None}).execute()
    cp(sb, 501, "@ali", "A", at(date(2026, 11, 28)))
    cp(sb, 501, "@ali", "A", at(date(2026, 12, 5)))
    cp(sb, 502, "@vali", "B", at(date(2026, 12, 6)))
    bot.sent.clear()
    await fs.tick(bot, at(date(2026, 12, 8)))
    d = [f for f in fines if f["object_name"] == "D"]
    assert len(d) == 1 and d[0]["user_id"] is None and d[0]["period_start"] == "2026-12-01"
    assert len(fines) == 2, fines
    msg = [(t, k) for c, t, k in bot.sent if c == admin and "belgilanmagan" in t]
    assert len(msg) == 1 and len(msg[0][1]["reply_markup"].inline_keyboard) == 3  # 2 ishchi + bekor qilish

    # Shaxsiy muddat: A ga 3 kun qo'yiladi — hisob o'sha kundan, eslatma 2 kun qolganda (bir marta), jarima 3 kundan keyin
    svc.set_period_days(1, 3, date(2026, 12, 8))
    assert svc.object_settings()[0] == {1: 3}
    bot.sent.clear()
    await fs.tick(bot, at(date(2026, 12, 8), 15))
    assert not [t for t in bot.to(501) if "Eslatma" in t]
    await fs.tick(bot, at(date(2026, 12, 9)))
    await fs.tick(bot, at(date(2026, 12, 10)))
    assert len([t for t in bot.to(501) if "Eslatma" in t and "3 kunlik" in t]) == 1
    await fs.tick(bot, at(date(2026, 12, 11)))
    a = [f for f in fines if f["object_name"] == "A"]
    assert len(a) == 1 and (a[0]["period_start"], a[0]["period_end"]) == ("2026-12-08", "2026-12-11")
    assert any("08.12–10.12.2026 — 3 kun ichida" in t for t in bot.to(501))
    # B standart 7 kunda qoladi: 04.12–10.12 da (06.12) checkpoint bor — jarima yo'q
    assert len([f for f in fines if f["object_name"] == "B"]) == 1
    # Standartga qaytarish
    svc.set_period_days(1, None, date(2026, 12, 11))
    assert svc.object_settings()[0] == {}
    await fs.tick(bot, at(date(2026, 12, 15)))
    assert len([f for f in fines if f["object_name"] == "A"]) == 1

    # Bot bir necha kun o'chib yonganda: o'tgan oy hisoboti qayta yuborilmaydi
    assert not [t for _, t, _ in bot.sent if "hisoboti" in t]
    print("OK: barcha testlar o'tdi")


if __name__ == "__main__":
    test_periods()
    asyncio.run(scenario())
