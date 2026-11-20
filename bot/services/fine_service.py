"""
Jarima tizimi — ma'lumotlar bazasi bilan ishlash va davr hisoblari.

Qoida: har bir obyektda boshlanish kunidan boshlab har FINE_PERIOD_DAYS kunda
kamida bitta qabul qilingan ("Keldi") checkpoint bo'lishi kerak. Bo'lmasa
obyektga mas'ul ishchiga (oxirgi checkpoint qilgan ishchi) jarima yoziladi.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from bot.database.db import get_supabase

TASHKENT = timezone(timedelta(hours=5))

LAUNCH_KEY = "fines_launch_date"


def now_local() -> datetime:
    return datetime.now(TASHKENT)


def parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def day_start_utc_iso(d: date) -> str:
    """Toshkent vaqti bilan kun boshlanishini UTC ISO ko'rinishida qaytaradi."""
    return datetime(d.year, d.month, d.day, tzinfo=TASHKENT).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def effective_start(start: date, launch: date) -> date:
    """Hisob boshlanadigan kun: tizim ishga tushgan kundan oldin jarima yozilmaydi."""
    return max(start, launch)


def due_periods(
    start: date,
    launch: date,
    checked_until: Optional[date],
    today: date,
    days: int,
) -> List[Tuple[date, date]]:
    """Tugagan, lekin hali tekshirilmagan davrlar: [(boshi, oxiri)), oxiri kirmaydi."""
    base = effective_start(start, launch)
    ps = base
    if checked_until and checked_until > base:
        done = -(-(checked_until - base).days // days)  # yuqoriga yaxlitlash
        ps = base + timedelta(days=done * days)
    out = []
    while ps + timedelta(days=days) <= today:
        out.append((ps, ps + timedelta(days=days)))
        ps += timedelta(days=days)
    return out


def current_period(start: date, launch: date, today: date, days: int) -> Optional[Tuple[date, date]]:
    """Bugun ichida bo'lgan davr. Hisob hali boshlanmagan bo'lsa None."""
    base = effective_start(start, launch)
    if today < base:
        return None
    k = (today - base).days // days
    ps = base + timedelta(days=k * days)
    return ps, ps + timedelta(days=days)


class FineService:
    def __init__(self):
        self.sb = get_supabase()

    # ── Sozlamalar ──

    def schema_ok(self) -> bool:
        """Migratsiya ishga tushirilganmi (jadval va ustunlar bormi)."""
        try:
            self.sb.table("bot_settings").select("key").limit(1).execute()
            self.sb.table("fines").select("id").limit(1).execute()
            self.sb.table("bot_users").select("user_id").limit(1).execute()
            self.sb.table("objects").select("id,start_date,fine_checked_until,fine_warned_period,start_asked_at").limit(1).execute()
            return True
        except Exception as e:
            print(f"❌ [FINES] Sxema tayyor emas: {e}")
            return False

    def get_setting(self, key: str) -> Optional[str]:
        """Xatolik bo'lsa exception ko'taradi — "yo'q" bilan adashtirmaslik uchun."""
        res = self.sb.table("bot_settings").select("value").eq("key", key).execute()
        return res.data[0]["value"] if res.data else None

    def set_setting(self, key: str, value: str) -> None:
        self.sb.table("bot_settings").upsert({"key": key, "value": value}).execute()

    def object_settings(self) -> Tuple[Dict[int, int], Dict[int, date]]:
        """Obyektlarning shaxsiy sozlamalari: ({id: muddat kunlarda}, {id: hisob qayta boshlangan kun})."""
        res = self.sb.table("bot_settings").select("*").limit(1000).execute()
        days: Dict[int, int] = {}
        anchors: Dict[int, date] = {}
        for row in res.data or []:
            key, value = row.get("key") or "", row.get("value")
            try:
                if key.startswith("obj_days:") and value:
                    days[int(key.split(":")[1])] = int(value)
                elif key.startswith("obj_anchor:") and parse_date(value):
                    anchors[int(key.split(":")[1])] = parse_date(value)
            except ValueError:
                continue
        return days, anchors

    def set_period_days(self, object_id: int, days: Optional[int], today: date) -> None:
        """Obyekt uchun muddatni o'zgartiradi (None — standart). Hisob shu kundan qaytadan boshlanadi."""
        self.set_setting(f"obj_days:{object_id}", str(days) if days else "")
        self.set_setting(f"obj_anchor:{object_id}", today.isoformat())
        self.sb.table("objects").update({
            "fine_checked_until": None,
            "fine_warned_period": None,
        }).eq("id", object_id).execute()

    def launch_date(self) -> Optional[date]:
        return parse_date(self.get_setting(LAUNCH_KEY))

    # ── Foydalanuvchilar ──

    def upsert_user(self, user_id: int, username: str, full_name: str) -> None:
        try:
            self.sb.table("bot_users").upsert(
                {"user_id": user_id, "username": username, "full_name": full_name}
            ).execute()
        except Exception as e:
            print(f"⚠️ [FINES] bot_users upsert xato: {e}")

    def known_workers(self) -> Dict[int, str]:
        """Botni ishlatgan barcha odamlar: {user_id: ko'rinadigan ism}."""
        workers: Dict[int, str] = {}
        res = self.sb.table("checkpoints").select("user_id,username").order("created_at", desc=True).limit(1000).execute()
        for row in res.data or []:
            uid = row.get("user_id")
            if uid and uid not in workers:
                workers[uid] = row.get("username") or str(uid)
        res = self.sb.table("bot_users").select("*").limit(1000).execute()
        for row in res.data or []:
            uid = row.get("user_id")
            if uid and uid not in workers:
                workers[uid] = row.get("username") or row.get("full_name") or str(uid)
        return workers

    # ── Obyektlar ──

    def objects(self) -> List[Dict[str, Any]]:
        res = self.sb.table("objects").select("*").order("name").execute()
        return res.data or []

    def get_object(self, object_id: int) -> Optional[Dict[str, Any]]:
        res = self.sb.table("objects").select("*").eq("id", object_id).execute()
        return res.data[0] if res.data else None

    def set_start_date(self, object_id: int, start: date) -> None:
        """Boshlanish sanasini saqlaydi va shu obyekt bo'yicha hisobni qaytadan boshlaydi."""
        self.sb.table("objects").update({
            "start_date": start.isoformat(),
            "fine_checked_until": None,
            "fine_warned_period": None,
        }).eq("id", object_id).execute()

    def mark_asked(self, object_id: int) -> None:
        self.sb.table("objects").update(
            {"start_asked_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", object_id).execute()

    def set_checked_until(self, object_id: int, until: date) -> None:
        self.sb.table("objects").update({"fine_checked_until": until.isoformat()}).eq("id", object_id).execute()

    def set_warned(self, object_id: int, period_start: date) -> None:
        self.sb.table("objects").update({"fine_warned_period": period_start.isoformat()}).eq("id", object_id).execute()

    # ── Checkpointlar ──

    def has_checkpoint(self, object_name: str, ps: date, pe: date) -> bool:
        res = self.sb.table("checkpoints").select("id")\
            .eq("object_name", object_name)\
            .eq("status", "Keldi")\
            .gte("created_at", day_start_utc_iso(ps))\
            .lt("created_at", day_start_utc_iso(pe))\
            .limit(1).execute()
        return bool(res.data)

    def last_worker(self, object_name: str) -> Optional[Tuple[int, str]]:
        """Obyektga mas'ul ishchi — oxirgi qabul qilingan checkpointni qilgan odam."""
        res = self.sb.table("checkpoints").select("user_id,username")\
            .eq("object_name", object_name)\
            .eq("status", "Keldi")\
            .order("created_at", desc=True)\
            .limit(1).execute()
        if not res.data or not res.data[0].get("user_id"):
            return None
        row = res.data[0]
        return row["user_id"], row.get("username") or str(row["user_id"])

    def fine_context(self, object_name: str, ps: date, pe: date) -> Dict[str, Any]:
        """Jarima sababi uchun: davrdan oldingi oxirgi va davrdan keyingi birinchi qabul qilingan checkpoint."""
        def to_local(row) -> Optional[date]:
            try:
                return datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")).astimezone(TASHKENT).date()
            except Exception:
                return None

        before = self.sb.table("checkpoints").select("created_at,username")\
            .eq("object_name", object_name).eq("status", "Keldi")\
            .lt("created_at", day_start_utc_iso(ps))\
            .order("created_at", desc=True).limit(1).execute()
        after = self.sb.table("checkpoints").select("created_at,username")\
            .eq("object_name", object_name).eq("status", "Keldi")\
            .gte("created_at", day_start_utc_iso(pe))\
            .order("created_at", desc=False).limit(1).execute()
        return {
            "last": to_local(before.data[0]) if before.data else None,
            "next": to_local(after.data[0]) if after.data else None,
            "next_user": after.data[0].get("username") if after.data else None,
        }

    def first_checkpoint_date(self, object_name: str) -> Optional[date]:
        res = self.sb.table("checkpoints").select("created_at")\
            .eq("object_name", object_name)\
            .order("created_at", desc=False)\
            .limit(1).execute()
        if not res.data:
            return None
        try:
            dt = datetime.fromisoformat(res.data[0]["created_at"].replace("Z", "+00:00"))
            return dt.astimezone(TASHKENT).date()
        except Exception:
            return None

    # ── Jarimalar ──

    def fine_exists(self, object_id: int, ps: date) -> bool:
        res = self.sb.table("fines").select("id").eq("object_id", object_id).eq("period_start", ps.isoformat()).execute()
        return bool(res.data)

    def create_fine(
        self,
        obj: Dict[str, Any],
        ps: date,
        pe: date,
        worker: Optional[Tuple[int, str]],
        amount: int,
    ) -> Dict[str, Any]:
        res = self.sb.table("fines").insert({
            "object_id": obj["id"],
            "object_name": obj["name"],
            "user_id": worker[0] if worker else None,
            "username": worker[1] if worker else None,
            "period_start": ps.isoformat(),
            "period_end": pe.isoformat(),
            "amount": amount,
        }).execute()
        return res.data[0]

    def get_fine(self, fine_id: int) -> Optional[Dict[str, Any]]:
        res = self.sb.table("fines").select("*").eq("id", fine_id).execute()
        return res.data[0] if res.data else None

    def cancel_fine(self, fine_id: int) -> None:
        self.sb.table("fines").update({"status": "cancelled"}).eq("id", fine_id).execute()

    def assign_fine(self, fine_id: int, user_id: int, username: str) -> None:
        self.sb.table("fines").update({"user_id": user_id, "username": username}).eq("id", fine_id).execute()

    def unreported_fines(self, until: date) -> List[Dict[str, Any]]:
        """Hali oylik hisobotga kirmagan, `until` kunigacha (shu kun ham) yozilgan faol jarimalar."""
        res = self.sb.table("fines").select("*")\
            .eq("status", "active")\
            .lte("period_end", until.isoformat())\
            .order("period_end", desc=False)\
            .limit(1000).execute()
        return [f for f in (res.data or []) if not f.get("reported")]

    def mark_reported(self, fine_ids: List[int]) -> None:
        for fid in fine_ids:
            self.sb.table("fines").update({"reported": True}).eq("id", fid).execute()

    def month_fines(self, year: int, month: int, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Jarima yozilgan sana (davr oxiri) shu oyga to'g'ri keladigan faol jarimalar."""
        first = date(year, month, 1)
        nxt = date(year + (month == 12), month % 12 + 1, 1)
        q = self.sb.table("fines").select("*")\
            .eq("status", "active")\
            .gte("period_end", first.isoformat())\
            .lt("period_end", nxt.isoformat())
        if user_id is not None:
            q = q.eq("user_id", user_id)
        res = q.order("period_end", desc=False).limit(1000).execute()
        return res.data or []
