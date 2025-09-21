import sqlite3
import glob
import os
from lxml import etree

# --- 1. Connexion SQLite ---
conn = sqlite3.connect("loup_solitare.db")
cur = conn.cursor()

# Supprimer si elles existent déjà
cur.execute("DROP TABLE IF EXISTS books")
cur.execute("DROP TABLE IF EXISTS sections")
cur.execute("DROP TABLE IF EXISTS choices")
cur.execute("DROP TABLE IF EXISTS illustrations")

# Créer les tables
cur.execute("""
CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    language TEXT,
    author TEXT,
    filename TEXT
)
""")

cur.execute("""
CREATE TABLE sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER,
    section_id TEXT,
    title TEXT,
    content TEXT,
    FOREIGN KEY(book_id) REFERENCES books(id)
)
""")

cur.execute("""
CREATE TABLE choices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id TEXT,
    target_id TEXT,
    text TEXT,
    FOREIGN KEY(section_id) REFERENCES sections(section_id)
)
""")

cur.execute("""
CREATE TABLE illustrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id TEXT,
    src TEXT,
    mime_type TEXT,
    width INTEGER,
    height INTEGER,
    FOREIGN KEY(section_id) REFERENCES sections(section_id)
)
""")

# --- 2. Fonction pour traiter un fichier XML ---
def process_xml(filepath):
    parser = etree.XMLParser(load_dtd=True, resolve_entities=True, recover=True)
    try:
        tree = etree.parse(filepath, parser)
        root = tree.getroot()
    except Exception as e:
        print(f"⚠️ Erreur en lisant {filepath} : {e}")
        return

    # Métadonnées du livre
    book_title = root.findtext("./meta/title", default="Unknown")
    book_lang = root.get("{http://www.w3.org/XML/1998/namespace}lang", "en")
    author_tag = root.find("./meta/creator[@class='author']")
    book_author = author_tag.text if author_tag is not None else "Unknown"

    cur.execute("INSERT INTO books (title, language, author, filename) VALUES (?, ?, ?, ?)",
                (book_title, book_lang, book_author, os.path.basename(filepath)))
    book_id = cur.lastrowid

    print(f"📖 Livre ajouté : {book_title} ({book_lang}) par {book_author}")

    # Sections
    for section in root.findall(".//section[@class='numbered']"):
        sec_id = section.get("id")
        sec_title = section.findtext("./meta/title")

        # Concaténer les paragraphes
        paragraphs = [p.text for p in section.findall(".//p") if p.text]
        content = "\n".join(paragraphs)

        cur.execute("INSERT INTO sections (book_id, section_id, title, content) VALUES (?, ?, ?, ?)",
                    (book_id, sec_id, sec_title, content))

        # --- Récupérer les illustrations ---
        for illu in section.findall(".//illustration/instance"):
            src = illu.get("src")
            mime = illu.get("mime-type")
            width = illu.get("width")
            height = illu.get("height")

            cur.execute("""
                INSERT INTO illustrations (section_id, src, mime_type, width, height)
                VALUES (?, ?, ?, ?, ?)
            """, (sec_id, src, mime, width, height))

        # Choix
        for choice in section.findall(".//choice"):
            target = choice.get("idref")
            text = choice.findtext("link-text")
            cur.execute("INSERT INTO choices (section_id, target_id, text) VALUES (?, ?, ?)",
                        (sec_id, target, text))

# --- 3. Parcourir tous les XML du dossier ---
xml_dir = "./project-aon-master/en/xml/"
for filepath in glob.glob(os.path.join(xml_dir, "*.xml")):
    process_xml(filepath)

# --- 4. Sauvegarder ---
conn.commit()
conn.close()

print("✅ Import terminé ! Tous les fichiers XML ont été traités.")
