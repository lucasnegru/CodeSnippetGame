import json
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, jsonify
from sqlalchemy import String, cast
from models import db, Snippet, Attempt
import atexit
import tempfile
import os
import re


def create_app(temp_db_path=None):
    app = Flask(__name__)

    #Datenbank-URI
    if temp_db_path is None:
        # temporäre Datei erstellen
        fd, temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)  # Datei wird nur von SQLAlchemy genutzt
        # Datei nach App-Exit löschen
        atexit.register(lambda: os.remove(temp_db_path) if os.path.exists(temp_db_path) else None)

    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{temp_db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    #Datenbank und Snippets initialisieren
    with app.app_context():
        db.drop_all()
        db.create_all()

        base_path = Path("../data")

        sources = [("ao", "ao_snippets.json"), ("io", "io_snippets.json")]
        items = []

        for category, filename in sources:
            file_path = base_path / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8-sig")
                data_list = json.loads(content)

                for row in data_list:
                    # Wenn Template leer, Standardfeld {{1}} setzen
                    tpl = row.get("code_template")
                    if not tpl:
                        tpl = "{{1}}"

                    # Wenn Sprache fehlt, 'general' setzen
                    lang = row.get("language")
                    if not lang:
                        lang = "general"

                    items.append(Snippet(
                        category=category,
                        title=row["title"],
                        language=lang,
                        level=row["level"],
                        prompt=row["prompt"],
                        code_template=tpl,
                        solution=row["solution"],
                        accepted=row.get("accepted"),
                        blocks=row.get("blocks"),
                        tips=row.get("tips"),
                        tags=row.get("tags"),
                    ))

        db.session.add_all(items)
        db.session.commit()

    #Routes
    @app.route("/")
    def index():
        cat = request.args.get("category", "ao")
        lang = request.args.get("language")
        level = request.args.get("level", type=int)
        tag = request.args.get("tag")

        q = Snippet.query
        if cat: q = q.filter_by(category=cat)
        if lang: q = q.filter_by(language=lang)
        if level: q = q.filter_by(level=level)
        if tag: q = q.filter(cast(Snippet.tags, String).like(f'%"{tag}"%'))

        snippets = q.order_by(getattr(Snippet, "level").asc(), Snippet.id.asc()).all()
        completed = {snip.id: Attempt.is_completed(snip.id) for snip in snippets}

        return render_template("index.html", snippets=snippets, completed=completed,
                               current_cat=cat, lang=lang, level=level, tag=tag)

    @app.route("/snippet/<int:sid>")
    def snippet_view(sid):
        snip = Snippet.query.get_or_404(sid)
        gaps = sorted(set(int(x) for x in re.findall(r"{{(\d+)}}", snip.code_template)))

        # Nächste Aufgabe nur aus gleicher Kategorie
        next_snip = Snippet.query.filter(
            Snippet.id > sid,
            Snippet.category == snip.category
        ).order_by(Snippet.id.asc()).first()

        return render_template("snippet.html", snip=snip, gaps=gaps, next_snip=next_snip)
    
    @app.route("/random")
    def random_snippet():
        cat = request.args.get("category")
        q = Snippet.query
        if cat: q = q.filter_by(category=cat)
        snip = q.order_by(db.func.random()).first()
        if not snip: return redirect(url_for("index"))
        return redirect(url_for("snippet_view", sid=snip.id))

    @app.post("/check/<int:sid>")
    def check(sid):
        snip = Snippet.query.get_or_404(sid)
        data = request.get_json(silent=True) or {}
        user_answers = data.get("answers", [])

        #Normierung
        def norm(s: str) -> str:
            s = (s or "").strip()
            s = re.sub(r"\s+", " ", s)
            if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
                return f'"{s[1:-1]}"'
            return s

        target = snip.solution or []
        accepted = snip.accepted or [None] * len(target)
        results = []
        all_ok = True

        for i, ta in enumerate(target, start=1):
            ua = user_answers[i - 1] if i - 1 < len(user_answers) else ""
            ua_n = norm(ua)
            pool = [ta]
            extra = accepted[i - 1] if i - 1 < len(accepted) and accepted[i - 1] else []
            if isinstance(extra, list):
                pool.extend(extra)
            elif extra:
                pool.append(extra)

            ok = False
            for patt in pool:
                p_str = str(patt) if patt is not None else ""

                if ua_n == norm(p_str): ok = True; break

                if p_str.startswith("re:"):
                    try:
                        if re.fullmatch(p_str[3:], ua): ok = True; break
                    except Exception:
                        pass

                if patt and not p_str.startswith("re:"):
                    try:
                        if ua_n.lower() == p_str.lower(): ok = True; break
                        if re.fullmatch(p_str, ua): ok = True; break
                    except Exception:
                        pass

            results.append({"index": i, "correct": ok, "expected": norm(ta), "got": ua_n})
            if not ok: all_ok = False

        att = Attempt(snippet_id=snip.id, user_answer=user_answers, is_correct=all_ok)
        db.session.add(att)
        db.session.commit()

        return jsonify({"ok": all_ok, "results": results})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(use_reloader=False)
