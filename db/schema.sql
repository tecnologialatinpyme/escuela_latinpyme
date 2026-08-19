-- ═══════════════════════════════════════════════════════
-- schema.sql — Escuela LatinPyme
-- Ejecuta este SQL en: Supabase → SQL Editor → New query
-- ═══════════════════════════════════════════════════════

-- ── Tabla de conversaciones de WhatsApp ──
CREATE TABLE IF NOT EXISTS conversations (
    phone       TEXT PRIMARY KEY,
    data        JSONB NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ DEFAULT NULL
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
    last_login  TIMESTAMPTZ,
    deleted_at  TIMESTAMPTZ DEFAULT NULL
);

-- ── Tabla de registro de actividad ──
CREATE TABLE IF NOT EXISTS activity_log (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,
    detail      TEXT,
    ts          TIMESTAMPTZ DEFAULT NOW()
);

-- ── Tabla de prompts de IA por aula ──
CREATE TABLE IF NOT EXISTS ai_prompts (
    id          BIGSERIAL PRIMARY KEY,
    aula_id     TEXT NOT NULL UNIQUE,
    aula_nombre TEXT NOT NULL,
    prompt      TEXT NOT NULL,
    activo      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ DEFAULT NULL
);

-- ── Tabla de estado IA por conversación ──
CREATE TABLE IF NOT EXISTS ai_conversation_config (
    phone       TEXT PRIMARY KEY,
    ai_enabled  BOOLEAN DEFAULT TRUE,
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ DEFAULT NULL
);

-- ── Migraciones / Actualizaciones para tablas existentes ──
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE ai_prompts ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE ai_conversation_config ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;

-- ── Deshabilitar Row Level Security (RLS) para acceso con service key ──
ALTER TABLE conversations DISABLE ROW LEVEL SECURITY;
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE activity_log DISABLE ROW LEVEL SECURITY;
ALTER TABLE ai_prompts DISABLE ROW LEVEL SECURITY;
ALTER TABLE ai_conversation_config DISABLE ROW LEVEL SECURITY;

-- ── Confirmación ──
SELECT 'Tablas y columnas actualizadas correctamente' AS resultado;

