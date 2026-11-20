-- Jarima tizimi uchun migratsiya.
-- Supabase → SQL Editor'ga joylab, bir marta "Run" bosing. Qayta ishga tushirsa ham zarar qilmaydi.

-- Obyekt ochilgan (hisob boshlanadigan) kun va xizmat ustunlari
alter table public.objects add column if not exists start_date date;
alter table public.objects add column if not exists start_asked_at timestamptz;
alter table public.objects add column if not exists fine_checked_until date;
alter table public.objects add column if not exists fine_warned_period date;

-- Jarimalar
create table if not exists public.fines (
    id bigint generated always as identity primary key,
    object_id bigint not null,
    object_name text not null,
    user_id bigint,
    username text,
    period_start date not null,
    period_end date not null,
    amount numeric not null default 50,
    status text not null default 'active',      -- active | cancelled
    reported boolean not null default false,    -- oylik hisobotga kirganmi
    created_at timestamptz not null default now(),
    unique (object_id, period_start)
);

-- Bot sozlamalari (ishga tushgan kun, yuborilgan hisobotlar)
create table if not exists public.bot_settings (
    key text primary key,
    value text,
    updated_at timestamptz not null default now()
);

-- Botdan foydalanuvchilar (e'lon va hisobot yuborish uchun)
create table if not exists public.bot_users (
    user_id bigint primary key,
    username text,
    full_name text,
    created_at timestamptz not null default now()
);

grant all on public.fines, public.bot_settings, public.bot_users to service_role;
