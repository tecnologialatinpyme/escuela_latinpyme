import os
from flask import Flask, redirect, url_for
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
    
    # Configurar clave secreta para la sesión
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'latinpyme_super_secret_session_key')
    
    # Cargar configuraciones del JSON al Flask config para disponibilidad global
    app.config.update(get_config())

    # Registrar todos los Blueprints dinámicamente
    for blueprint, url_prefix in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint, url_prefix=url_prefix)

    # Redirección de la raíz al Dashboard
    @app.route('/')
    def index():
        return redirect('/dashboard')

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)