from flask import Blueprint, render_template, jsonify
from flask_login import login_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    """Renderiza el panel de estadísticas y KPIs."""
    return render_template('dashboard.html')

@dashboard_bp.route('/api/stats', methods=['GET'])
@login_required
def api_stats():
    """Retorna las estadísticas reales acumuladas en el servidor."""
    try:
        from routes.conversations import conversations_store
        active_chats = len(conversations_store)
        total_outbound = 0

        for num, conv in conversations_store.items():
            for msg in conv.get('messages', []):
                if msg.get('direction') == 'out':
                    total_outbound += 1

        return jsonify({
            'exito': True,
            'active_chats': active_chats,
            'total_outbound': total_outbound
        })
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500

