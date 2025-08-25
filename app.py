import json
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, jsonify
from sqlalchemy import String, cast
from models import db, Snippet, Attempt
import atexit
import tempfile
import os

def create_app(temp_db_path=None):
    app = Flask(__name__)
    #Datenbank-URI
    if temp_db_path is None:
        # temporäre Datei erstellen
        fd, temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)  # Datei wird nur von SQLAlchemy genutzt
        # Datei nach App-Exit löschen
        atexit.register(lambda: os.remove(temp_db_path) if os.path.exists(temp_db_path) else None)

    app.config["DATA_PATH"] = Path("data/snippets.json")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{temp_db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    #Datenbank und Snippets initialisieren
    with app.app_context():
        db.drop_all()
        db.create_all()

        if not app.config["DATA_PATH"].exists():
            raise SystemExit(f"Datendatei fehlt: {app.config["DATA_PATH"].resolve()}")

        data = json.loads(app.config["DATA_PATH"].read_text(encoding="utf-8"))
        items = [
            Snippet(
                title=row["title"],
                language=row["language"],
                level=row["level"],
                prompt=row["prompt"],
                code_template=row["code_template"],
                solution=row["solution"],
                accepted=row.get("accepted"),
                blocks=row.get("blocks"),
                tips=row.get("tips"),
                tags=row.get("tags"),
            )
            for row in data
        ]
        db.session.add_all(items)
        db.session.commit()

    #Routes
    @app.route("/")
    def index():
        lang = request.args.get("language")
        level = request.args.get("level", type=int)
        tag = request.args.get("tag")
        q = Snippet.query
        if lang:
            q = q.filter_by(language=lang)
        if level:
            q = q.filter_by(level=level)
        if tag:
            q = q.filter(cast(Snippet.tags, String).like(f'%"{tag}"%'))
        snippets = q.order_by(getattr(Snippet, "level").asc(),Snippet.id.asc()).all()
        return render_template("index.html", snippets=snippets, lang=lang, level=level, tag=tag)

    @app.route("/snippet/<int:sid>")
    def snippet_view(sid):
        import re as _re
        snip = Snippet.query.get_or_404(sid)
        gaps = sorted(set(int(x) for x in _re.findall(r"{{(\d+)}}", snip.code_template)))
        return render_template("snippet.html", snip=snip, gaps=gaps)

    @app.route("/random")
    def random_snippet():
        lang = request.args.get("language")
        level = request.args.get("level", type=int)
        q = Snippet.query
        if lang:
            q = q.filter_by(language=lang)
        if level:
            q = q.filter_by(level=level)
        snip = q.order_by(db.func.random()).first()
        if not snip:
            return redirect(url_for("index"))
        return redirect(url_for("snippet_view", sid=snip.id))

    @app.post("/check/<int:sid>")
    def check(sid):
        snip = Snippet.query.get_or_404(sid)
        data = request.get_json(silent=True) or {}
        user_answers = data.get("answers", [])

        # hier kann deine Normierungs-Logik bleiben...
        # Beispiel:
        from re import sub, fullmatch
        def norm(s: str) -> str:
            s = (s or "").strip()
            s = sub(r"\s+", " ", s)
            if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
                inner = s[1:-1]
                return f'"{inner}"'
            return s

        target = snip.solution or []
        accepted = snip.accepted or [None] * len(target)
        results = []
        all_ok = True

        for i, ta in enumerate(target, start=1):
            ua = user_answers[i-1] if i-1 < len(user_answers) else ""
            ua_n = norm(ua)
            ta_n = norm(ta)

            pool = [ta]
            extra = accepted[i-1] if i-1 < len(accepted) and accepted[i-1] else []
            if isinstance(extra, list):
                pool.extend(extra)
            elif extra:
                pool.append(extra)

            ok = False
            for patt in pool:
                patt_n = norm(patt or "")
                if ua_n == patt_n:
                    ok = True
                    break
                if isinstance(patt, str) and patt.startswith("re:"):
                    regex = patt[3:]
                    try:
                        if fullmatch(regex, ua):
                            ok = True
                            break
                    except Exception:
                        pass
                if snip.level >= 3 and patt and not patt.startswith("re:"):
                    try:
                        if fullmatch(patt, ua):
                            ok = True
                            break
                    except Exception:
                        pass

            results.append({"index": i, "correct": ok, "expected": ta_n, "got": ua_n})
            if not ok:
                all_ok = False

        att = Attempt(snippet_id=snip.id, user_answer=user_answers, is_correct=all_ok)
        db.session.add(att)
        db.session.commit()

        return jsonify({"ok": all_ok, "results": results})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
