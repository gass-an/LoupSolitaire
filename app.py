import os
from flask import Flask, render_template, g, send_from_directory, abort
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "lonewolf.db")
IMAGE_ROOT = os.path.join(BASE_DIR, "project-aon-master", "en", "jpeg")

app = Flask(__name__)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def get_books_by_category():
    """Utilise la colonne books.category pour regrouper."""
    db = get_db()
    books = db.execute("SELECT * FROM books ORDER BY code").fetchall()
    grouped = {"lw": [], "gs": [], "fw": []}
    for b in books:
        cat = (b["category"] or "lw").lower()
        grouped.setdefault(cat, []).append(b)
    return grouped

@app.route("/")
def index():
    books_by_cat = get_books_by_category()
    return render_template("index.html", books_by_cat=books_by_cat)

@app.route("/cover/<cat>/<code>")
def cover(cat, code):
    """
    Sert l'image de couverture selon la catégorie et le code.
    """
    base_dir = os.path.join(IMAGE_ROOT, cat, code, "skins", "ebook")
    for filename in ("cover.jpg", "cover.jpeg", "cover.png"):
        path = os.path.join(base_dir, filename)
        if os.path.isfile(path):
            return send_from_directory(base_dir, filename)
    abort(404)

if __name__ == "__main__":
    app.run(debug=True)
