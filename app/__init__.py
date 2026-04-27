from __future__ import annotations

import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("app.config.Config")

    if test_config is not None:
        app.config.update(test_config)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    db.init_app(app)

    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp
    from app.routes.librarian import librarian_bp
    from app.routes.member import member_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(member_bp, url_prefix="/member")
    app.register_blueprint(librarian_bp, url_prefix="/librarian")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    with app.app_context():
        # Ensure all models are imported before creating tables.
        from app import models  # noqa: F401

        db.create_all()

    return app
