from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, and_
from sqlalchemy.types import JSON  # generischer JSON-Typ, funktioniert mit SQLite als TEXT-Fallback

db = SQLAlchemy()

class Snippet(db.Model):
    __tablename__ = "snippets"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    language = db.Column(db.String(16), nullable=False)  # "python" | "java"
    level = db.Column(db.Integer, nullable=False)         # 1..4
    prompt = db.Column(db.Text, nullable=False)
    code_template = db.Column(db.Text, nullable=False)    # mit {{1}}, {{2}} ...
    solution = db.Column(JSON, nullable=False)            # z. B. ["x", "print(\"ok\")"]
    accepted = db.Column(JSON, nullable=True)             # optionale Alternativen pro Lücke: [ ["x"], ["print('ok')","re:^print\\(.+\\)$"] ]
    blocks = db.Column(JSON, nullable=True)               # Bausteine (Buttons)
    tips = db.Column(JSON, nullable=True)                 # Hinweise
    tags = db.Column(JSON, nullable=True)                 # ["strings","loops"]

    __table_args__ = (
        CheckConstraint("level >= 1 AND level <= 4", name="level_range"),
    )

    def __init__(self, title, language, level, prompt, code_template, solution, accepted=None, blocks=None, tips=None, tags=None):
        self.title = title
        self.language = language
        self.level = level
        self.prompt = prompt
        self.code_template = code_template
        self.solution = solution
        self.accepted = accepted
        self.blocks = blocks
        self.tips = tips
        self.tags = tags

class Attempt(db.Model):
    __tablename__ = "attempts"
    id = db.Column(db.Integer, primary_key=True)
    snippet_id = db.Column(db.Integer, db.ForeignKey("snippets.id"), nullable=False)
    user_answer = db.Column(JSON, nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __init__(self, snippet_id, user_answer, is_correct=False):
        self.snippet_id = snippet_id
        self.user_answer = user_answer
        self.is_correct = is_correct

    @staticmethod
    def is_completed(sid: int) -> bool:
        return db.session.query(Attempt.id).filter_by(
            snippet_id=sid,
            is_correct=True
        ).first() is not None