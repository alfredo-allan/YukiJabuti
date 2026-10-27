"""API do Yuki Jabuti — Flask + SQLite (pronta para o PythonAnywhere)."""
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from config import Config
from sqlalchemy import inspect, text

from models import db
from routes import api


def create_app(config=Config):
    app = Flask(__name__)
    app.config.from_object(config)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("Defina a variável de ambiente SECRET_KEY (veja o README).")

    origens = [o.strip() for o in app.config["FRONTEND_ORIGIN"].split(",") if o.strip()]
    CORS(app, resources={r"/api/*": {"origins": origens}})

    db.init_app(app)
    app.register_blueprint(api)

    @app.errorhandler(HTTPException)
    def erro(e):
        msg = e.description if e.code in (400, 401, 404, 429) else "Algo deu errado no servidor."
        if e.code == 413:
            msg = "O arquivo enviado é grande demais."
        return jsonify({"erro": msg}), e.code

    with app.app_context():
        db.create_all()
        _migrar_schema()
    return app


def _migrar_schema():
    """Adds columns introduced after the initial SQLite schema without resetting data."""
    inspector = inspect(db.engine)
    additions = {
        "jabuti": {"foto_tipo": "VARCHAR(30)"},
        "registro": {"foto": "TEXT", "foto_tipo": "VARCHAR(30)"},
    }
    for table, columns in additions.items():
        existing = {column["name"] for column in inspector.get_columns(table)}
        for name, definition in columns.items():
            if name not in existing:
                db.session.execute(text(
                    f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}'
                ))
    db.session.commit()


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
