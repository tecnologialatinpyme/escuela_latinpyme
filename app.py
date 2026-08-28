import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from routes import ALL_BLUEPRINTS
from config import get_config


def create_app() -> Flask:
    """
    Application Factory para la plataforma Escuela LatinPyme.
    Inicializa el servidor, registra las rutas modulares y carga las configuraciones.
    """
    app = Flask(__name__)

    # Directorio temporal de cargas
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'static', 'uploads', 'media'), exist_ok=True)

    # Configurar clave secreta para la sesión
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'latinpyme_super_secret_session_key')

    # Cargar configuraciones del JSON al Flask config para disponibilidad global
    app.config.update(get_config())

    # ── Flask-Login ──
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'          # Redirige aquí si no está logueado
    login_manager.login_message = 'Por favor inicia sesión para continuar.'
    login_manager.login_message_category = 'error'

    @login_manager.user_loader
    def load_user(user_id):
        """Carga el usuario desde la BD usando el ID guardado en sesión."""
        from db import user_store
        from routes.auth import User
        data = user_store.get_user_by_id(int(user_id))
        if data:
            return User(data)
        return None

    # ── Inicializar base de datos (crea tablas si no existen) ──
    try:
        from db.database import init_db
        with app.app_context():
            init_db()
            _seed_admin_user()
    except Exception as e:
        print(f"[APP] Advertencia: No se pudo inicializar la BD: {e}")
        print("[APP] Asegúrate de que SUPABASE_URL y SUPABASE_SECRET_KEY estén configuradas en las variables de entorno.")

    # Registrar todos los Blueprints dinámicamente
    for blueprint, url_prefix in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint, url_prefix=url_prefix)

    # Redirección de la raíz al Login (protege el acceso al dashboard)
    @app.route('/')
    def index():
        return redirect('/auth/login')

    return app


def _seed_admin_user():
    """
    Crea el usuario admin por defecto si no existe ningún usuario en la BD.
    Solo se ejecuta en el primer arranque con BD vacía.
    """
    try:
        from db import user_store
        if user_store.count_users() == 0:
            result = user_store.create_user(
                username='admin',
                email='admin@latinpyme.com',
                password='LatinPyme2025!',
                full_name='Administrador',
                role='admin'
            )
            if result:
                print("[APP] Usuario admin creado. Credenciales: admin / LatinPyme2025!")
                print("[APP] IMPORTANTE: Cambia la contrasena despues del primer login.")
    except Exception as e:
        print(f"[APP] Advertencia al verificar o sembrar usuario admin: {e}")



app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)