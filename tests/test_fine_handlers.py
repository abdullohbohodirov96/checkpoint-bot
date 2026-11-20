"""
Jarima handlerlari testi (soxta xabar va callback bilan).
Ishga tushirish: python -m tests.test_fine_handlers
"""

import asyncio
from datetime import date
from types import SimpleNamespace

from tests.test_fines import FakeBot, FakeSupabase, at, cp  # muhit o'zgaruvchilarini ham sozlaydi
from bot.database import db
from bot.handlers import fines as h
from bot.services import fine_scheduler as fs
from bot.services.fine_service import now_local

ADMIN = fs.settings.FINE_ADMIN_ID


class State:
    def __init__(self): self.state, self.data = None, {}
    async def clear(self): self.state, self.data = None, {}
    async def set_state(self, s): self.state = s
    async def update_data(self, **kw): self.data.update(kw)
    async def get_data(self): return dict(self.data)


class Msg:
    def __init__(self, bot, uid, text=None):
        self.bot, self.text, self.out = bot, text, []
        self.from_user = SimpleNamespace(id=uid)
        self.chat = SimpleNamespace(id=uid)
    async def answer(self, text, **kw): self.out.append(text)
    async def edit_text(self, text, **kw): self.out.append(text)


class Cb:
    def __init__(self, bot, uid, data):
        self.data, self.from_user, self.message, self.alerts = data, SimpleNamespace(id=uid), Msg(bot, uid), []
    async def answer(self, text=None, **kw): self.alerts.append(text)


async def main():
    sb = FakeSupabase()
    db._supabase = sb
    bot = FakeBot()
    for t in ("fines", "bot_settings", "bot_users", "checkpoints"):
        sb.store.setdefault(t, [])
    sb.table("objects").insert({"name": "A <1>", "created_at": "2026-09-01T00:00:00+00:00", "start_date": None,
                                "start_asked_at": None, "fine_checked_until": "2026-11-27", "fine_warned_period": None}).execute()
    today = now_local().date()
    cp(sb, 501, "@ali", "A <1>", at(date(2026, 11, 10)))
    svc = fs.FineService()
    first = today.replace(day=1)
    fine = svc.create_fine({"id": 1, "name": "A <1>"}, first, first.replace(day=8), (501, "@ali"), 50)
    free = svc.create_fine({"id": 1, "name": "A <1>"}, first.replace(day=8), first.replace(day=15), None, 50)

    # Ishchi: o'z jarimalari sababi bilan
    await h.my_fines(Msg(bot, 501, "💰 Jarimalarim"), State())
    text = "\n".join(bot.to(501))
    assert "A &lt;1&gt;" in text and "Jami: 1 ta" in text and "Qoida" in text and "checkpoint qilinmadi" in text
    bot.sent.clear()
    await h.my_fines(Msg(bot, 777, "💰 Jarimalarim"), State())
    assert "jarimangiz yo'q" in "\n".join(bot.to(777))

    # Admin: joriy oy + sanasi yo'q obyektlar; admin bo'lmagan odamga javob yo'q
    bot.sent.clear()
    m = Msg(bot, 501, "💰 Jarimalar")
    await h.admin_fines(m, State())
    assert not m.out and not bot.sent
    await h.admin_fines(Msg(bot, ADMIN, "💰 Jarimalar"), State())
    text = "\n".join(bot.to(ADMIN))
    assert "Joriy oy jarimalari" in text and "Ishchi belgilanmagan" in text and "kiritilmagan obyektlar: 1 ta" in text

    # Boshlanish sanasi: bugundan / tayyor sana / qo'lda; hisob qaytadan boshlanadi
    c = Cb(bot, 501, "fstart:today:1")
    await h.start_date_today(c)
    assert sb.store["objects"][0]["start_date"] is None and c.alerts == ["⛔️ Ruxsat yo'q!"]
    await h.start_date_today(Cb(bot, ADMIN, "fstart:today:1"))
    assert sb.store["objects"][0]["start_date"] == today.isoformat()
    assert sb.store["objects"][0]["fine_checked_until"] is None
    await h.start_date_set(Cb(bot, ADMIN, "fstart:set:1:20260901"))
    assert sb.store["objects"][0]["start_date"] == "2026-09-01"
    st = State()
    await h.start_date_custom(Cb(bot, ADMIN, "fstart:custom:1"), st)
    bad = Msg(bot, ADMIN, "ertaga")
    await h.start_date_entered(bad, st)
    assert "noto'g'ri" in bad.out[0] and st.state is not None
    ok = Msg(bot, ADMIN, "15/11/2026")
    await h.start_date_entered(ok, st)
    assert sb.store["objects"][0]["start_date"] == "2026-11-15" and st.state is None and "15.11.2026" in ok.out[0]
    await h.start_dates_list(Cb(bot, ADMIN, "fstart:list"))
    await h.start_date_pick(Cb(bot, ADMIN, "fstart:pick:1"), bot)

    # Jarimani ishchiga biriktirish va bekor qilish
    bot.sent.clear()
    await h.fine_assign(Cb(bot, ADMIN, f"fine:assign:{free['id']}:501"), bot)
    assert sb.store["fines"][1]["user_id"] == 501 and sb.store["fines"][1]["username"] == "@ali"
    assert any("jarima yozildi" in t for t in bot.to(501))
    c = Cb(bot, ADMIN, f"fine:assign:{free['id']}:501")
    await h.fine_assign(c, bot)
    assert "allaqachon" in c.alerts[0]
    bot.sent.clear()
    await h.fine_cancel(Cb(bot, ADMIN, f"fine:cancel:{fine['id']}"), bot)
    assert sb.store["fines"][0]["status"] == "cancelled" and any("bekor qilindi" in t for t in bot.to(501))
    c = Cb(bot, 501, f"fine:cancel:{free['id']}")
    await h.fine_cancel(c, bot)
    assert sb.store["fines"][1]["status"] == "active"
    print("OK: handler testlari o'tdi")


if __name__ == "__main__":
    asyncio.run(main())
