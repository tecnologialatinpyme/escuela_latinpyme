-- ═══════════════════════════════════════════════════════
-- schema.sql — Escuela LatinPyme
-- Ejecuta este SQL en: Supabase → SQL Editor → New query
-- ═══════════════════════════════════════════════════════

-- ── Tabla de usuarios del sistema ──
CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL,
    full_name   TEXT NOT NULL,
    role        TEXT DEFAULT 'asesor' CHECK (role IN ('admin', 'asesor')),
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    last_login  TIMESTAMPTZ,
    deleted_at  TIMESTAMPTZ DEFAULT NULL
);

-- ── Tabla de conversaciones de WhatsApp ──
CREATE TABLE IF NOT EXISTS conversations (
    phone          TEXT PRIMARY KEY,
    assigned_to    BIGINT REFERENCES users(id) ON DELETE SET NULL,
    data           JSONB NOT NULL DEFAULT '{}',
    name           TEXT,
    avatar         TEXT,
    unread         INT DEFAULT 0,
    last_message   TEXT,
    last_ts        TIMESTAMPTZ,
    human_required BOOLEAN DEFAULT FALSE,
    updated_at     TIMESTAMPTZ DEFAULT NOW(),
    deleted_at     TIMESTAMPTZ DEFAULT NULL
);

-- ── Tabla de mensajes de conversaciones (Normalizada) ──
CREATE TABLE IF NOT EXISTS messages (
    id                  BIGSERIAL PRIMARY KEY,
    conversation_phone  TEXT NOT NULL REFERENCES conversations(phone) ON DELETE CASCADE,
    wa_message_id       TEXT UNIQUE,
    direction           TEXT NOT NULL CHECK (direction IN ('in', 'out')),
    body                TEXT NOT NULL DEFAULT '',
    ts                  TIMESTAMPTZ DEFAULT NOW(),
    ia_generated        BOOLEAN DEFAULT FALSE,
    disparador          TEXT DEFAULT NULL,
    wa_sent             BOOLEAN DEFAULT TRUE,
    simulado            BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ DEFAULT NULL,
    status              TEXT DEFAULT 'sent' CHECK (status IN ('sent', 'delivered', 'read', 'failed'))
);
ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_message_id TEXT UNIQUE;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'sent';


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
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS assigned_to BIGINT REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS avatar TEXT;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS unread INT DEFAULT 0;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_message TEXT;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_ts TIMESTAMPTZ;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS human_required BOOLEAN DEFAULT FALSE;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;

ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE ai_prompts ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE ai_conversation_config ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;

-- Restricción de rol (si no existía)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'check_user_role'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT check_user_role CHECK (role IN ('admin', 'asesor'));
    END IF;
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

-- ── Tabla de Contactos del Sistema ──
CREATE TABLE IF NOT EXISTS contacts (
    id          BIGSERIAL PRIMARY KEY,
    phone       TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    email       TEXT DEFAULT NULL,
    company     TEXT DEFAULT NULL,
    cargo       TEXT DEFAULT NULL,
    ciudad      TEXT DEFAULT NULL,
    aula_id     TEXT DEFAULT NULL,
    aula_nombre TEXT DEFAULT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ DEFAULT NULL
);

-- ── Índices Parciales para Rendimiento y Escalabilidad ──
CREATE INDEX IF NOT EXISTS idx_conversations_deleted_at ON conversations(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_conversations_assigned_to ON conversations(assigned_to) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_messages_conv_ts ON messages(conversation_phone, ts DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_messages_deleted_at ON messages(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_deleted_at ON users(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_activity_log_user_ts ON activity_log(user_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_ai_prompts_aula_id ON ai_prompts(aula_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_deleted_at ON contacts(deleted_at) WHERE deleted_at IS NULL;

-- ── Deshabilitar Row Level Security (RLS) para acceso con service key ──
ALTER TABLE conversations DISABLE ROW LEVEL SECURITY;
ALTER TABLE messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE activity_log DISABLE ROW LEVEL SECURITY;
ALTER TABLE ai_prompts DISABLE ROW LEVEL SECURITY;
ALTER TABLE ai_conversation_config DISABLE ROW LEVEL SECURITY;
ALTER TABLE contacts DISABLE ROW LEVEL SECURITY;

-- ── Confirmación ──
SELECT 'Tablas, índices parciales y restricciones actualizados correctamente' AS resultado;


