from flask import Blueprint, render_template

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    """Renderiza el panel de estadísticas y KPIs."""
    return render_template('dashboard.html')
