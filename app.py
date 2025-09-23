import os
import re
from markupsafe import Markup
from flask import Flask, render_template, g, send_from_directory, abort, url_for
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "lonewolf.db")
IMAGE_ROOT = os.path.join(BASE_DIR, "project-aon-master", "en", "jpeg")

# Prépare les racines d’images d’illustrations (Project Aon stocke souvent en gif/png)
GIF_ROOT = os.path.join(BASE_DIR, "project-aon-master", "en", "gif")
PNG_ROOT = os.path.join(BASE_DIR, "project-aon-master", "en", "png")
JPEG_ROOT = os.path.join(BASE_DIR, "project-aon-master", "en", "jpeg")  # parfois utilisé

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

@app.route("/book/<code>")
def book_detail(code):
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE code = ?", (code.lower(),)).fetchone()
    if not book:
        abort(404)
    cover_url = url_for('cover', cat=book['category'], code=book['code'])
    return render_template("book.html", book=book, cover_url=cover_url)

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

def resolve_illu_url(category: str, code: str, rel_src: str):
    """
    Résout l'URL d'une illustration en testant PNG -> JPEG -> GIF.
    1) Essaye le chemin donné (normalisé) et /ill/<basename>
    2) Si introuvable, cherche récursivement le basename sous en/<fmt>/<cat>/<code>/**
    """
    if not rel_src:
        return None

    # normaliser le src
    rel_src_norm = rel_src.replace("\\", "/").lstrip("./")
    rel_src_norm = os.path.normpath(rel_src_norm).replace("\\", "/")
    basename = os.path.basename(rel_src_norm)

    # candidats "directs"
    direct_candidates_rel = [rel_src_norm]
    if not rel_src_norm.lower().startswith("ill/") and basename:
        direct_candidates_rel.append(f"ill/{basename}")

    roots = [("png", PNG_ROOT), ("jpeg", JPEG_ROOT), ("gif", GIF_ROOT)]
    tried = []

    # 1) essais directs
    for fmt, base_root in roots:
        for rel_try in direct_candidates_rel:
            fullpath = os.path.join(base_root, category, code, rel_try.replace("/", os.sep))
            if os.path.isfile(fullpath):
                return url_for("illu", fmt=fmt, cat=category, code=code, path=rel_try)
            tried.append(fullpath)

    # 2) recherche récursive sur le basename
    for fmt, base_root in roots:
        code_dir = os.path.join(base_root, category, code)
        if not os.path.isdir(code_dir):
            continue
        # walk une seule fois par fmt
        for root, _dirs, files in os.walk(code_dir):
            # match case-insensitive sur le basename
            for f in files:
                if f.lower() == basename.lower():
                    abs_found = os.path.join(root, f)
                    # chemin relatif depuis <fmt>/<cat>/<code>
                    rel_found = os.path.relpath(abs_found, code_dir).replace("\\", "/")
                    return url_for("illu", fmt=fmt, cat=category, code=code, path=rel_found)

    return None


def _render_content_xml(xml: str) -> str:
    """
    Rendu HTML très simple/tolérant du content_xml.
    - Remplace quelques balises Project Aon par du HTML.
    - Échappe ce qu'il faut le moins possible (ici, on suppose content_xml est clean).
    Adapte au besoin si tu veux un rendu plus riche.
    """
    if not xml:
        return ""
    # Entités custom (si tu n'as pas déjà fait le nettoyage à l'import)
    replacements = {
        "<ch.apos/>": "'",
        "<ch.ndash/>": "-",
        "<ch.mdash/>": "—",
        "<ch.hellip/>": "…",
        "<ch.amp/>": "&",
    }
    for k, v in replacements.items():
        xml = xml.replace(k, v)
    # Balises simples -> HTML
    xml = re.sub(r"</?para>", "", xml, flags=re.IGNORECASE)         # on laisse gérer les sauts par <br> ou <p> si besoin
    xml = re.sub(r"<emphasis>", "<em>", xml, flags=re.IGNORECASE)
    xml = re.sub(r"</emphasis>", "</em>", xml, flags=re.IGNORECASE)
    xml = re.sub(r"<strong>", "<strong>", xml, flags=re.IGNORECASE)
    xml = re.sub(r"</strong>", "</strong>", xml, flags=re.IGNORECASE)
    # Liste rapide (si présent)
    xml = re.sub(r"<list>", "<ul>", xml, flags=re.IGNORECASE)
    xml = re.sub(r"</list>", "</ul>", xml, flags=re.IGNORECASE)
    xml = re.sub(r"<item>", "<li>", xml, flags=re.IGNORECASE)
    xml = re.sub(r"</item>", "</li>", xml, flags=re.IGNORECASE)
    # Nettoyage choix/illustrations restés (on n'affiche pas les <choice> bruts)
    xml = re.sub(r"<choice\b.*?>.*?</choice>", "", xml, flags=re.IGNORECASE | re.DOTALL)
    xml = re.sub(r"<illustration\b.*?>.*?</illustration>", "", xml, flags=re.IGNORECASE | re.DOTALL)
    # Paragraphes basiques : split sur double saut
    parts = [p.strip() for p in re.split(r"\n\s*\n", xml) if p.strip()]
    html = "".join(f"<p>{p}</p>" for p in parts) if parts else xml
    return html

@app.route("/play/<code>/")
@app.route("/play/<code>/<sec_id>")
def play(code, sec_id=None):
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE code = ?", (code.lower(),)).fetchone()
    if not book:
        abort(404)

    # Défaut = sect1 ; sinon, fallback = plus petit numéro de 'sectXXX'
    if not sec_id:
        s = db.execute("""
            SELECT * FROM sections
            WHERE book_id=?
              AND sec_id='sect1'
            LIMIT 1
        """, (book["id"],)).fetchone()

        if not s:
            s = db.execute("""
                SELECT * FROM sections
                WHERE book_id=? AND sec_id LIKE 'sect%'
                ORDER BY CAST(SUBSTR(sec_id, 5) AS INT) ASC
                LIMIT 1
            """, (book["id"],)).fetchone()

        if not s:
            abort(404)
        sec_id = s["sec_id"]

    section = db.execute(
        "SELECT * FROM sections WHERE book_id=? AND sec_id=?",
        (book["id"], sec_id)
    ).fetchone()
    if not section:
        abort(404)

    # ❗ On ne prend que les CHOIX (pas les prev/next)
    choices = db.execute("""
        SELECT to_sec_ref, COALESCE(display_text, to_sec_ref) AS label
        FROM links
        WHERE book_id=? AND from_section=? AND rel='choice'
        ORDER BY id
    """, (book["id"], section["id"])).fetchall()

    # Illustrations de la section (identique à avant)
    illus = db.execute("""
        SELECT src, width, height, mime_type, variant_class
        FROM images WHERE book_id=? AND section_id=?
        ORDER BY id
    """, (book["id"], section["id"])).fetchall()

    content_html = Markup(_render_content_xml(section["content_xml"]))

    # Illustrations associées -> on construit les URLs avec fallback PNG -> JPEG -> GIF
    illu_urls = []
    for im in illus:
        u = resolve_illu_url(book["category"], book["code"], im["src"])
        if u:
            illu_urls.append(u)




    return render_template(
        "play.html",
        book=book,
        section=section,
        content_html=content_html,
        choices=choices,
        illu_urls=illu_urls
    )


@app.route("/illu/<fmt>/<cat>/<code>/<path:path>")
def illu(fmt, cat, code, path):
    """
    Sert une illustration depuis en/{gif|png|jpeg}/<cat>/<code>/<path>.
    """
    root_map = {"gif": GIF_ROOT, "png": PNG_ROOT, "jpeg": JPEG_ROOT}
    base = root_map.get(fmt.lower())
    if not base:
        abort(404)
    dir_path = os.path.join(base, cat, code, os.path.dirname(path))
    filename = os.path.basename(path)
    full = os.path.join(dir_path, filename)
    if not os.path.isfile(full):
        abort(404)
    return send_from_directory(dir_path, filename)


if __name__ == "__main__":
    app.run(debug=True)