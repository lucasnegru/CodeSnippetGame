import json
from pathlib import Path
from models import db, Snippet
from app import create_app

DATA_PATH = Path("data/snippets.json")

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()

    if not DATA_PATH.exists():
        raise SystemExit(f"Datendatei fehlt: {DATA_PATH.resolve()}")

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    items = []
    for row in data:
        items.append(Snippet(
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
        ))

    db.session.add_all(items)
    db.session.commit()
    print(f"Importiert: {len(items)} Snippets.")
