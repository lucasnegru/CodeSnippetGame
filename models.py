from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint
from sqlalchemy.types import JSON

db = SQLAlchemy()

class Snippet(db.Model):
    __tablename__ = "snippets"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    language = db.Column(db.String(16), nullable=False)  # "python" | "java"
    level = db.Column(db.Integer, nullable=False)         # 1..4
    prompt = db.Column(db.Text, nullable=False)
    code_template = db.Column(db.Text, nullable=False)    # with {{1}}, {{2}} ...
    solution = db.Column(JSON, nullable=False)            # ["Hello, world!"]
    blocks = db.Column(JSON, nullable=True)               # ["print", "(", ...]
    tips = db.Column(JSON, nullable=True)                 # ["Tipp 1", "Tipp 2"]

    __table_args__ = (
        CheckConstraint("level >= 1 AND level <= 4", name="level_range"),
    )

class Attempt(db.Model):
    __tablename__ = "attempts"
    id = db.Column(db.Integer, primary_key=True)
    snippet_id = db.Column(db.Integer, db.ForeignKey("snippets.id"), nullable=False)
    user_answer = db.Column(JSON, nullable=False)         # ["Hello, world!"]
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
