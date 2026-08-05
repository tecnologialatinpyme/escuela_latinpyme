from .dashboard import dashboard_bp
from .datacenter import datacenter_bp
from .campaigns import campaigns_bp
from .conversations import conversations_bp
from .settings import settings_bp

# Lista para iterar y registrar todos los blueprints
ALL_BLUEPRINTS = [
    (dashboard_bp, '/dashboard'),
    (datacenter_bp, '/datacenter'),
    (campaigns_bp, '/campaigns'),
    (conversations_bp, '/conversations'),
    (settings_bp, '/settings')
]
