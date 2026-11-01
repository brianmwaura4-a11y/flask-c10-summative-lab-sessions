import os

from flask import Flask, jsonify, request, session
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

db = SQLAlchemy()
bcrypt = Bcrypt()
migrate = Migrate()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///notes.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
        PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    frontend_origin = os.environ.get("FRONTEND_ORIGIN")
    if frontend_origin:
        CORS(app, origins=[frontend_origin], supports_credentials=True)

    from models import Note, User  

    def error(message, status):
        return jsonify(error=message), status

    def current_user():
        user_id = session.get("user_id")
        return db.session.get(User, user_id) if user_id else None

    def note_payload(note):
        return {"id": note.id, "title": note.title, "content": note.content,
                "created_at": note.created_at.isoformat(), "updated_at": note.updated_at.isoformat()}

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.post("/signup")
    @app.post("/api/auth/register")
    def register():
        data = request.get_json(silent=True) or {}
        username = data.get("username", "")
        password = data.get("password", "")
        confirmation = data.get("password_confirmation")
        if not isinstance(username, str) or not isinstance(password, str):
            return error("username and password must be strings", 400)
        username = username.strip()
        if not 3 <= len(username) <= 80 or len(password) < 8:
            return error("username must be 3–80 characters and password at least 8 characters", 400)
        if confirmation is None:
            return error("password_confirmation is required", 400)
        if confirmation != password:
            return error("password confirmation does not match", 400)
        user = User(username=username, password_hash=bcrypt.generate_password_hash(password).decode("utf-8"))
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return error("username is already registered", 409)
        session.clear()
        session["user_id"] = user.id
        session.permanent = True
        return jsonify(user.to_dict()), 201

    @app.post("/login")
    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True) or {}
        username, password = data.get("username", ""), data.get("password", "")
        user = User.query.filter_by(username=username.strip() if isinstance(username, str) else "").first()
        if not user or not isinstance(password, str) or not bcrypt.check_password_hash(user.password_hash, password):
            return error("invalid username or password", 401)
        session.clear()
        session["user_id"] = user.id
        session.permanent = True
        return jsonify(user.to_dict())

    @app.delete("/logout")
    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        return jsonify({})

    @app.get("/check_session")
    def check_session():
        user = current_user()
        return jsonify(user.to_dict() if user else {})

    @app.get("/api/auth/me")
    def me():
        user = current_user()
        return (jsonify(user.to_dict()), 200) if user else error("authentication required", 401)

    def require_user():
        user = current_user()
        return (user, None) if user else (None, error("authentication required", 401))

    @app.get("/notes")
    @app.get("/api/notes")
    def list_notes():
        user, failure = require_user()
        if failure:
            return failure
        try:
            page = max(1, int(request.args.get("page", 1)))
            per_page = min(100, max(1, int(request.args.get("per_page", 10))))
        except (TypeError, ValueError):
            return error("page and per_page must be integers", 400)
        pagination = Note.query.filter_by(user_id=user.id).order_by(Note.created_at.desc(), Note.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return jsonify(items=[note_payload(n) for n in pagination.items], page=page,
                       per_page=per_page, total=pagination.total, pages=pagination.pages)

    @app.post("/notes")
    @app.post("/api/notes")
    def create_note():
        user, failure = require_user()
        if failure:
            return failure
        data = request.get_json(silent=True) or {}
        title, content = data.get("title"), data.get("content")
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 200:
            return error("title is required and must be at most 200 characters", 400)
        if not isinstance(content, str) or not content.strip():
            return error("content is required", 400)
        note = Note(title=title.strip(), content=content.strip(), user_id=user.id)
        db.session.add(note)
        db.session.commit()
        return jsonify(note_payload(note)), 201

    @app.route("/notes/<int:note_id>", methods=["GET", "PATCH", "DELETE"])
    @app.route("/api/notes/<int:note_id>", methods=["GET", "PATCH", "DELETE"])
    def note_detail(note_id):
        user, failure = require_user()
        if failure:
            return failure
        note = Note.query.filter_by(id=note_id, user_id=user.id).first()
        if not note:
            return error("note not found", 404)
        if request.method == "GET":
            return jsonify(note_payload(note))
        if request.method == "DELETE":
            db.session.delete(note)
            db.session.commit()
            return "", 204
        data = request.get_json(silent=True) or {}
        if "title" in data:
            if not isinstance(data["title"], str) or not data["title"].strip() or len(data["title"].strip()) > 200:
                return error("title must be non-empty and at most 200 characters", 400)
            note.title = data["title"].strip()
        if "content" in data:
            if not isinstance(data["content"], str) or not data["content"].strip():
                return error("content must be non-empty", 400)
            note.content = data["content"].strip()
        if not (set(data) & {"title", "content"}):
            return error("provide title or content to update", 400)
        db.session.commit()
        return jsonify(note_payload(note))

    @app.errorhandler(404)
    def not_found(_):
        return error("endpoint not found", 404)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5555)),
            debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
