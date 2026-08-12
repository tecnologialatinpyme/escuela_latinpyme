-- ═══════════════════════════════════════════════════════
-- schema.sql — Escuela LatinPyme
-- Ejecuta este SQL en: Supabase → SQL Editor → New query
-- ═══════════════════════════════════════════════════════

-- ── Tabla de conversaciones de WhatsApp ──
CREATE TABLE IF NOT EXISTS conversations (
    phone       TEXT PRIMARY KEY,
    data        JSONB NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Tabla de usuarios del sistema ──
CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL,
    full_name   TEXT NOT NULL,
    role        TEXT DEFAULT 'asesor',
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    last_login  TIMESTAMPTZ
);

-- ── Tabla de registro de actividad ──
CREATE TABLE IF NOT EXISTS activity_log (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,
    detail      TEXT,
    ts          TIMESTAMPTZ DEFAULT NOW()
);

-- ── Deshabilitar Row Level Security (RLS) para acceso con service key ──
-- Esto permite que el backend acceda con SUPABASE_SECRET_KEY sin restricciones
ALTER TABLE conversations DISABLE ROW LEVEL SECURITY;
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE activity_log DISABLE ROW LEVEL SECURITY;

-- ── Confirmación ──
SELECT 'Tablas creadas correctamente' AS resultado;
