from models import db, Snippet
from app import create_app

app = create_app()
samples = [
    # Level 1 – Python
    Snippet(
        title="Hallo Welt ausgeben",
        language="python",
        level=1,
        prompt="Gib den Text Hello, world! aus.",
        code_template='print({{1}})\n',
        solution=["\"Hello, world!\""],
        blocks=["\"Hello, world!\""],
        tips=["Nutze die print-Funktion.", "Strings stehen in Anführungszeichen."]
    ),
    # Level 2 – Java
    Snippet(
        title="Summe bilden",
        language="java",
        level=2,
        prompt="Addiere zwei Zahlen und speichere das Ergebnis in sum.",
        code_template='int sum = {{1}} + {{2}};\nSystem.out.println(sum);\n',
        solution=["2", "3"],
        blocks=["2","3","4","5"],
        tips=["In Java endet eine Anweisung mit Semikolon."]
    ),
    # Level 3 – Python
    Snippet(
        title="If-Bedingung",
        language="python",
        level=3,
        prompt="Prüfe, ob x größer als 10 ist und gib ok aus.",
        code_template='x = 12\nif {{1}} > 10:\n    {{2}}\n',
        solution=["x", 'print("ok")'],
        blocks=["x", 'print("ok")', 'print("no")'],
        tips=["Einrückung ist wichtig in Python."]
    ),
    # Level 4 – Java
    Snippet(
        title="Array aufsummieren",
        language="java",
        level=4,
        prompt="Summiere alle Elemente eines int-Arrays numbers.",
        code_template='int total = 0;\nfor (int i = 0; i < {{1}}.length; i++) {\n    total += {{1}}[i];\n}\nSystem.out.println(total);\n',
        solution=["numbers"],
        blocks=["numbers"],
        tips=["Denke an length für Arrays."]
    ),
]

with app.app_context():
    db.drop_all(); db.create_all()
    db.session.add_all(samples)
    db.session.commit()
    print("Seeded.")
