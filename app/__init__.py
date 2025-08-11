from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.models import db




def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = 'gizli_anahtar'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://DILARA_CELIK\\SQLEXPRESS/yonetici_db?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Blueprint’leri import et
    from app.routes import main
    app.register_blueprint(main)

    return app
