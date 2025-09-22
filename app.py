from flask import Flask, render_template, g
import sqlite3

app = Flask(__name__)
DATABASE = "./data/loup_solitare.db"

# --- Connexion à la DB ---
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

# --- Route page titre (accueil) ---
@app.route("/")
def titre():
    db = get_db()
    book = db.execute("SELECT * FROM books LIMIT 1").fetchone()
    if not book:
        return "Aucun livre trouvé", 404

    # Première section avec section_id valide
    first_section = db.execute(
        "SELECT * FROM sections WHERE book_id=? AND section_id IS NOT NULL ORDER BY id ASC LIMIT 1",
        (book["id"],)
    ).fetchone()
    if not first_section:
        return "Aucune section trouvée", 404

    # Choix et illustrations filtrés
    liens = db.execute(
        "SELECT * FROM choices WHERE section_id=? AND target_id IS NOT NULL",
        (first_section["section_id"],)
    ).fetchall()

    illustrations = db.execute(
        "SELECT * FROM illustrations WHERE section_id=? AND src IS NOT NULL",
        (first_section["section_id"],)
    ).fetchall()

    return render_template("page.html", section=first_section, liens=liens, illustrations=illustrations)

# --- Route section spécifique ---
@app.route("/section/<section_id>")
def section(section_id):
    db = get_db()
    section = db.execute(
        "SELECT * FROM sections WHERE section_id=?",
        (section_id,)
    ).fetchone()
    if not section:
        return "Section non trouvée", 404

    liens = db.execute(
    "SELECT * FROM choices WHERE section_id=? AND target_id IS NOT NULL",
    (section_id,)
    ).fetchall()

    illustrations = db.execute(
    "SELECT DISTINCT src, mime_type, width, height FROM illustrations WHERE section_id=? AND src IS NOT NULL",
    (section["section_id"],)
    ).fetchall()


    return render_template("page.html", section=section, liens=liens, illustrations=illustrations)

if __name__ == "__main__":
    app.run(debug=True)
