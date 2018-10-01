from flask import Flask
import os

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    if app.config['ENV'] == 'production':
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['SQLALCHEMY_DATABASE_URI']
        app.secret_key = os.environ['FLASK_SECRET_KEY']
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../development.db'
        app.secret_key = '42'

    from .models import db, init_db
    db.init_app(app)
    app.cli.add_command(init_db)

    from .views import login_manager, root
    login_manager.init_app(app)
    app.register_blueprint(root)

    return app
