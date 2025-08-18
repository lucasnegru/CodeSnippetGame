import re
from flask import Flask, render_template, request, redirect, url_for, jsonify
from models import db, Snippet, Attempt

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///puzzles.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

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
            # einfache Filterung über JSON: enthält tag als Substring im serialisierten Feld
            q = q.filter(Snippet.tags.like(f'%"{tag}"%'))
        snippets = q.order_by(Snippet.level.asc(), Snippet.id.asc()).all()
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
        user_answers = request.json.get("answers", [])

        def norm(s: str) -> str:
            s = (s or "").strip()
            s = re.sub(r"\s+", " ", s)
            # vereinheitliche einfache/doppelte Quotes für string-literals
            if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
                inner = s[1:-1]
                return f"\"{inner}\""
            return s

        target = snip.solution or []
        accepted = snip.accepted or [None] * len(target)

        results = []
        all_ok = True

        for i, ta in enumerate(target, start=1):
            ua = user_answers[i-1] if i-1 < len(user_answers) else ""
            ua_n = norm(ua)
            ta_n = norm(ta)

            # akzeptierte Varianten-Liste zusammenbauen
            pool = [ta]  # immer die Hauptlösung
            extra = accepted[i-1] if i-1 < len(accepted) and accepted[i-1] is not None else []
            if isinstance(extra, list):
                pool.extend(extra)
            else:
                if extra:  # String
                    pool.append(extra)

            ok = False
            # Level 1-2: exakte Übereinstimmung (mit Normalisierung) ODER explizite regex via "re:..."
            # Level 3-4: exakte Übereinstimmung ODER Regex-Match (für alle "re:..." Einträge; außerdem Direkt-Regex bei target erlaubt)
            for patt in pool:
                patt = patt or ""
                patt_n = norm(patt)
                if ua_n == patt_n:
                    ok = True
                    break
                # Regex-Einträge: "re:<pattern>"
                if isinstance(patt, str) and patt.startswith("re:"):
                    regex = patt[3:]
                    try:
                        if re.fullmatch(regex, ua):
                            ok = True
                            break
                    except re.error:
                        pass
                # bei Level >=3 kann die Hauptlösung selbst als Regex interpretiert werden, falls gültig
                if snip.level >= 3 and patt and not patt.startswith("re:"):
                    try:
                        if re.fullmatch(patt, ua):
                            ok = True
                            break
                    except re.error:
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
    with app.app_context():
        db.create_all()
    app.run(debug=True)
