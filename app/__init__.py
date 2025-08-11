from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# TEK ve MERKEZİ db nesnesi
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    from config import Config
    app.config.from_object(Config)

    # db'yi bu app'e bağla
    db.init_app(app)

    # Modelleri ve blueprint'leri init_app'ten SONRA import et
    from . import models                 # tablolar kaydolur
    from .routes import main as main_bp  # varsa blueprint

    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()  # SQLite tabloları oluştur

    return app
