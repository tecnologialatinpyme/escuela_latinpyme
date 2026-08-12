from .dashboard import dashboard_bp
from .datacenter import datacenter_bp
from .campaigns import campaigns_bp
from .conversations import conversations_bp
from .settings import settings_bp
from .auth import auth_bp
from .admin import admin_bp
from .ai_assistant import ai_assistant_bp

# Lista para iterar y registrar todos los blueprints
ALL_BLUEPRINTS = [
    (auth_bp,          '/auth'),
    (admin_bp,         '/admin'),
    (dashboard_bp,     '/dashboard'),
    (datacenter_bp,    '/datacenter'),
    (campaigns_bp,     '/campaigns'),
    (conversations_bp, '/conversations'),
    (settings_bp,      '/settings'),
    (ai_assistant_bp,  '/ai-assistant'),
]

