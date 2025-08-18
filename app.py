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
        q = Snippet.query
        if lang: q = q.filter_by(language=lang)
        if level: q = q.filter_by(level=level)
        snippets = q.order_by(Snippet.level.asc(), Snippet.id.asc()).all()
        return render_template("index.html", snippets=snippets, lang=lang, level=level)

    @app.route("/snippet/<int:sid>")
    def snippet_view(sid):
        snip = Snippet.query.get_or_404(sid)
        # Anzahl Lücken = Anzahl {{N}} im Template
        gaps = sorted(set(int(x) for x in re.findall(r"{{(\d+)}}", snip.code_template)))
        return render_template("snippet.html", snip=snip, gaps=gaps)

    @app.route("/random")
    def random_snippet():
        lang = request.args.get("language")
        level = request.args.get("level", type=int)
        q = Snippet.query
        if lang: q = q.filter_by(language=lang)
        if level: q = q.filter_by(level=level)
        snip = q.order_by(db.func.random()).first()
        if not snip:
            return redirect(url_for("index"))
        return redirect(url_for("snippet_view", sid=snip.id))

    @app.post("/check/<int:sid>")
    def check(sid):
        snip = Snippet.query.get_or_404(sid)
        user_answers = request.json.get("answers", [])
        # Normalisierung: trim + einfache Whitespaces normieren
        def norm(s: str) -> str:
            s = (s or "").strip()
            s = re.sub(r"\s+", " ", s)
            # für Python/Java Strings: vereinheitliche Quotes
            if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
                inner = s[1:-1]
                return f"\"{inner}\""
            return s

        target = snip.solution or []
        # Toleranter Vergleich bei Level >=3: exakter Match ODER Regex
        results = []
        all_ok = True
        for i, ta in enumerate(target, start=1):
            ua = user_answers[i-1] if i-1 < len(user_answers) else ""
            ua_n = norm(ua)
            ta_n = norm(ta)
            ok = False
            if snip.level <= 2:
                ok = (ua_n == ta_n)
            else:
                # exakter Treffer oder Regex-Match
                try:
                    ok = (ua_n == ta_n) or bool(re.fullmatch(ta, ua))
                except re.error:
                    ok = (ua_n == ta_n)
            results.append({"index": i, "correct": ok, "expected": ta_n, "got": ua_n})
            if not ok: all_ok = False

        # Optional: speichern
        att = Attempt(snippet_id=snip.id, user_answer=user_answers, is_correct=all_ok)
        db.session.add(att); db.session.commit()

        return jsonify({"ok": all_ok, "results": results})

    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
