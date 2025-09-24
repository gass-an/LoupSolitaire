#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_aon_fs.py
---------------
Construit une base SQLite pour Lone Wolf (Project Aon) à partir d'un dossier
décompressé, sans arguments.

- Dossier source (XML) : ./project-aon-master
- Base SQLite : ./data/lonewolf.db

Usage :
    python build_aon_fs.py
"""

import os
import re
import sqlite3
import sys
import json
from glob import glob
from typing import Dict, List, Optional, Tuple

# ----- Chemins -----
SOURCE_ROOT = r"./project-aon-master"      # dossier déjà UNZIP
DB_PATH     = r"./data/lonewolf.db"        # base à créer

LANG_FILTER_PREFIX = "en"   # ne prend que les XML en anglais
ONLY_CODES = set()          # exemple: {"01fftd", "02fotw"}

# ---------- Utilitaires parsing ----------

_SECTION_OPEN_TAG = re.compile(r'<section[^>]*\bid="([^"]+)"[^>]*>', re.IGNORECASE)
_SECTION_CLASS = re.compile(r'class="([^"]+)"')
_META_BLOCK = re.compile(r"<meta>(.*?)</meta>", re.DOTALL | re.IGNORECASE)
_META_TITLE = re.compile(r"<title>(.*?)</title>", re.DOTALL | re.IGNORECASE)
_META_LINK = re.compile(r'<link\s+class="([^"]+)"\s+idref="([^"]+)"\s*/?>', re.IGNORECASE)
_DATA_BLOCK = re.compile(r"<data>(.*?)</data>", re.DOTALL | re.IGNORECASE)
_CHOICE = re.compile(r'<choice\s+idref="([^"]+)"[^>]*>(.*?)</choice>', re.DOTALL | re.IGNORECASE)
_LINK_TEXT = re.compile(r"<link-text>(.*?)</link-text>", re.DOTALL | re.IGNORECASE)
_ILLUSTRATION = re.compile(r"<illustration[^>]*>(.*?)</illustration>", re.DOTALL | re.IGNORECASE)
_INSTANCE = re.compile(r'<instance\s+[^>]*src="([^"]+)"[^>]*/>', re.IGNORECASE)
_ATTR_CLASS = re.compile(r'class="([^"]+)"', re.IGNORECASE)
_ATTR_WIDTH = re.compile(r'width="([^"]+)"', re.IGNORECASE)
_ATTR_HEIGHT = re.compile(r'height="([^"]+)"', re.IGNORECASE)
_ATTR_MIME = re.compile(r'mime-type="([^"]+)"', re.IGNORECASE)
_GAMEBOOK_TITLE = re.compile(r"<gamebook[^>]*>.*?<meta>.*?<title>(.*?)</title>", re.DOTALL | re.IGNORECASE)
_XML_LANG = re.compile(r'xml:lang="([^"]+)"', re.IGNORECASE)
_BLURB_BLOCK = re.compile(r'<([a-zA-Z0-9:_-]+)[^>]*\bclass="[^"]*\bblurb\b[^"]*"[^>]*>(.*?)</\1>', re.IGNORECASE | re.DOTALL)
_COMBAT_BLOCK = re.compile(r"<combat\b[^>]*>(.*?)</combat>", re.IGNORECASE | re.DOTALL)
_ENEMY_NAME = re.compile(r"<enemy>(.*?)</enemy>", re.IGNORECASE | re.DOTALL)
_ENEMY_ATTR = re.compile(r'<enemy-attribute[^>]*\bclass="([^"]+)"[^>]*>(.*?)</enemy-attribute>', re.IGNORECASE | re.DOTALL)


ENTITY_MAP = {
    "<ch.apos/>": "'",
    "<ch.ndash/>": "-",
    "<ch.mdash/>": "—",
    "<ch.hellip/>": "…",
    "<ch.amp/>": "&",
    # ajoute ici d’autres entités Project Aon si besoin
}

def clean_entities(text: str) -> str:
    if not text:
        return text
    for k, v in ENTITY_MAP.items():
        text = text.replace(k, v)
    return text


def _balance_section_block(xml: str, start_tag_pos: int) -> Tuple[int, int]:
    n = len(xml)
    i = start_tag_pos
    j = xml.find(">", i)
    if j == -1:
        raise ValueError("Balise <section> mal formée")
    count = 0
    k = i
    while k < n:
        if xml.startswith("<section", k):
            count += 1
            k = xml.find(">", k) + 1
        elif xml.startswith("</section>", k):
            count -= 1
            k += len("</section>")
            if count == 0:
                return (i, k)
        else:
            k += 1
    raise ValueError("Section non équilibrée")

def extract_section_by_id(xml: str, sec_id: str) -> Optional[str]:
    pattern = re.compile(rf'<section[^>]*\bid="{re.escape(sec_id)}"[^>]*>', re.IGNORECASE)
    m = pattern.search(xml)
    if not m:
        return None
    start, end = _balance_section_block(xml, m.start())
    return xml[start:end]

def extract_meta(block_xml: str) -> Tuple[Optional[str], List[Dict[str, str]], str]:
    m = _META_BLOCK.search(block_xml)
    meta_xml = m.group(1) if m else ""
    mt = _META_TITLE.search(meta_xml)
    title = mt.group(1).strip() if mt else None
    links = [{"rel": lm.group(1), "target": lm.group(2)} for lm in _META_LINK.finditer(meta_xml)]
    return title, links, meta_xml

def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text, flags=re.DOTALL).strip()

def extract_data(block_xml: str) -> Tuple[str, List[Dict[str, str]], List[Dict[str, Optional[str]]]]:
    m = _DATA_BLOCK.search(block_xml)
    data_xml = m.group(1) if m else ""

    choices = []
    for cm in _CHOICE.finditer(data_xml):
        target = cm.group(1)
        inner = cm.group(2)

        # Texte complet sans balises (y compris link-text)
        full_text = strip_tags(inner).strip()

        # Texte du link-text (seulement "turn to 141") si besoin
        lm = _LINK_TEXT.search(inner)
        link_text = lm.group(1).strip() if lm else None

        choices.append({
            "target": target,
            "display": full_text,     # phrase complète
            "link_text": link_text,   # en plus si tu veux
            "raw": inner
        })

    images = []
    for im in _ILLUSTRATION.finditer(data_xml):
        inner = im.group(1)
        chosen = None
        for inm in _INSTANCE.finditer(inner):
            tag = inm.group(0)
            src = inm.group(1)
            cls = _ATTR_CLASS.search(tag)
            w = _ATTR_WIDTH.search(tag)
            h = _ATTR_HEIGHT.search(tag)
            mime = _ATTR_MIME.search(tag)
            rec = {
                "src": src,
                "class": cls.group(1) if cls else None,
                "width": w.group(1) if w else None,
                "height": h.group(1) if h else None,
                "mime": mime.group(1) if mime else None,
            }
            if (cls and cls.group(1) == "html") or chosen is None:
                chosen = rec
                if cls and cls.group(1) == "html":
                    break
        if chosen:
            images.append(chosen)

    combats = []
    for cm in _COMBAT_BLOCK.finditer(data_xml):
        inner = cm.group(1)
        enemies = []

        # Un bloc <combat> peut lister plusieurs <enemy> avec leurs <enemy-attribute>
        # On regroupe par "groupe logique": soit (enemy + ses attrs), soit attrs seuls.
        # 1) essaie pattern "enemy + attrs suivants"
        chunks = re.split(r"(?i)(?=<enemy>)", inner)
        if len(chunks) > 1:
            idx = 0
            for ch in chunks:
                if not ch.strip():
                    continue
                mname = _ENEMY_NAME.search(ch)
                name = strip_tags(mname.group(1)).strip() if mname else None
                attrs = dict()
                for am in _ENEMY_ATTR.finditer(ch):
                    cls = am.group(1).strip().lower()
                    val = strip_tags(am.group(2)).strip()
                    attrs[cls] = val
                enemies.append({"index": idx, "name": name,
                                "cs": int(attrs.get("combatskill")) if attrs.get("combatskill") else None,
                                "ep": int(attrs.get("endurance")) if attrs.get("endurance") else None,
                                "extra": {k:v for k,v in attrs.items() if k not in ("combatskill","endurance")}})
                idx += 1
        else:
            # 2) Pas de <enemy> distincts : on prend juste les attrs globaux comme un ennemi anonyme
            attrs = dict((am.group(1).strip().lower(), strip_tags(am.group(2)).strip())
                         for am in _ENEMY_ATTR.finditer(inner))
            if attrs:
                enemies.append({"index": 0, "name": None,
                                "cs": int(attrs.get("combatskill")) if attrs.get("combatskill") else None,
                                "ep": int(attrs.get("endurance")) if attrs.get("endurance") else None,
                                "extra": {k:v for k,v in attrs.items() if k not in ("combatskill","endurance")}})

        if enemies:
            combats.append({"enemies": enemies, "raw": inner})

    return data_xml, choices, images, combats

def read_text_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="latin-1") as f:
            return f.read()


def parse_book_from_file(xml_path: str) -> Dict:
    raw = read_text_file(xml_path)

    # Titre / code / langue
    mt = _GAMEBOOK_TITLE.search(raw)
    book_title = mt.group(1).strip() if mt else os.path.basename(xml_path)
    book_title = clean_entities(book_title)

    code = os.path.splitext(os.path.basename(xml_path))[0].lower()
    mlang = _XML_LANG.search(raw)
    lang = (mlang.group(1) if mlang else "en").lower()

    # Synopsis : 1er bloc avec class="blurb"
    synopsis_text = None
    m_blurb = _BLURB_BLOCK.search(raw)
    if m_blurb:
        synopsis_text = strip_tags(m_blurb.group(2)).strip()

    # Sections listées : "title" (si présent) + sect###
    sect_ids = [m.group(1) for m in re.finditer(r'id="(sect\d+)"', raw, flags=re.IGNORECASE)]
    include_special = set()
    if re.search(r'<section[^>]*\bid="title"', raw, flags=re.IGNORECASE):
        include_special.add("title")

    sections, links, images, combats = [], [], [], []
    ordered_ids = list(include_special) + sorted(sect_ids, key=lambda x: int(x[4:]))

    for sid in ordered_ids:
        block = extract_section_by_id(raw, sid)
        if not block:
            continue

        # Meta & titre de section
        sec_title, meta_links, _meta_raw = extract_meta(block)
        sec_title = clean_entities(sec_title)

        # Corps + choix + illustrations + combats (⚠ extract_data doit renvoyer 4 valeurs)
        data_xml, choices, imgs, cmbs = extract_data(block)
        data_xml = clean_entities(data_xml)

        # Classe de section
        mclass = _SECTION_CLASS.search(block)
        sclass = mclass.group(1) if mclass else None

        # Section
        sections.append({
            "id": sid,
            "title": sec_title,
            "class": sclass,
            "content": data_xml.strip()
        })

        # Liens méta
        for lnk in meta_links:
            links.append({
                "from": sid, "to": lnk["target"], "rel": lnk["rel"],
                "display": None, "raw": None
            })

        # Choix (phrase complète déjà mise en display par extract_data)
        for ch in choices:
            links.append({
                "from": sid, "to": ch["target"], "rel": "choice",
                "display": ch["display"], "raw": ch["raw"]
            })

        # Illustrations
        for im in imgs:
            images.append({
                "section": sid,
                "src": im["src"],
                "class": im.get("class"),
                "width": im.get("width"),
                "height": im.get("height"),
                "mime": im.get("mime"),
            })

        # ⚔️ Combats
        for cb in cmbs:
            combats.append({
                "section": sid,
                "enemies": cb["enemies"]  # liste de {index,name,cs,ep,extra}
            })

    return {
        "code": code,
        "title": book_title,
        "lang": lang,
        "sections": sections,
        "links": links,
        "images": images,
        "combats": combats,               # <— AJOUT
        "synopsis": synopsis_text or None
    }



# ---------- SQLite ----------

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS books (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    code      TEXT NOT NULL UNIQUE,
    title     TEXT NOT NULL,
    language  TEXT NOT NULL,
    category  TEXT,
    synopsis  TEXT
);


CREATE TABLE IF NOT EXISTS sections (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id       INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    sec_id        TEXT NOT NULL,
    class         TEXT,
    title         TEXT,
    content_xml   TEXT NOT NULL,
    UNIQUE(book_id, sec_id)
);


CREATE TABLE IF NOT EXISTS links (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id        INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    from_section   INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    to_sec_ref     TEXT NOT NULL,
    rel            TEXT NOT NULL,
    display_text   TEXT,
    raw_xml        TEXT
);


CREATE TABLE IF NOT EXISTS images (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id        INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    section_id     INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    src            TEXT NOT NULL,
    width          TEXT,
    height         TEXT,
    mime_type      TEXT,
    variant_class  TEXT
);

-- Combat blocks trouvés dans une section
CREATE TABLE IF NOT EXISTS combats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id     INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    section_id  INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    note        TEXT    -- texte libre éventuel (non obligatoire)
);

-- Ennemis d'un bloc de combat (un combat peut avoir 1+ ennemis)
CREATE TABLE IF NOT EXISTS combat_enemies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    combat_id   INTEGER NOT NULL REFERENCES combats(id) ON DELETE CASCADE,
    enemy_index INTEGER NOT NULL,     -- ordre d'apparition (0..n-1)
    name        TEXT,                 -- <enemy>
    cs          INTEGER,              -- <enemy-attribute class="combatskill">
    ep          INTEGER,              -- <enemy-attribute class="endurance">
    extra_json  TEXT                  -- autres attributs éventuels (JSON)
);


CREATE INDEX IF NOT EXISTS idx_sections_book_sec ON sections(book_id, sec_id);
CREATE INDEX IF NOT EXISTS idx_links_from ON links(book_id, from_section);
CREATE INDEX IF NOT EXISTS idx_links_to   ON links(book_id, to_sec_ref);
CREATE INDEX IF NOT EXISTS idx_images_section ON images(section_id);
CREATE INDEX IF NOT EXISTS idx_combats_section ON combats(section_id);
CREATE INDEX IF NOT EXISTS idx_cenemies_combat ON combat_enemies(combat_id);
"""

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()

def upsert_book(conn: sqlite3.Connection, code: str, title: str, language: str, category: str, synopsis: Optional[str]) -> int:
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO books(code, title, language, category, synopsis)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(code) DO UPDATE
           SET title=excluded.title,
               language=excluded.language,
               category=excluded.category,
               synopsis=COALESCE(excluded.synopsis, books.synopsis)""",
        (code, title, language, category, synopsis)
    )
    conn.commit()
    cur.execute("SELECT id FROM books WHERE code = ?", (code,))
    return cur.fetchone()[0]


def insert_sections_links_images(conn: sqlite3.Connection, book_id: int, book: Dict) -> None:
    cur = conn.cursor()
    sec_id_to_rowid: Dict[str, int] = {}

    for s in book["sections"]:
        cur.execute(
            "INSERT OR REPLACE INTO sections(book_id, sec_id, class, title, content_xml) "
            "VALUES (?, ?, ?, ?, ?)",
            (book_id, s["id"], s["class"], s["title"], s["content"])
        )
        cur.execute("SELECT id FROM sections WHERE book_id=? AND sec_id=?", (book_id, s["id"]))
        sec_rowid = cur.fetchone()[0]
        sec_id_to_rowid[s["id"]] = sec_rowid

    for l in book["links"]:
        from_rowid = sec_id_to_rowid.get(l["from"])
        if not from_rowid:
            continue
        cur.execute(
            "INSERT INTO links(book_id, from_section, to_sec_ref, rel, display_text, raw_xml) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (book_id, from_rowid, l["to"], l["rel"], l["display"], l["raw"])
        )

    for im in book["images"]:
        section_rowid = sec_id_to_rowid.get(im["section"])
        if not section_rowid:
            continue
        cur.execute(
            "INSERT INTO images(book_id, section_id, src, width, height, mime_type, variant_class) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (book_id, section_rowid, im["src"], im["width"], im["height"], im["mime"], im["class"])
        )

    insert_combats(conn, book_id, book, sec_id_to_rowid)

    conn.commit()

def find_category_from_cover(code: str) -> str:
    """
    Cherche dans en/jpeg/<cat>/<code>/skins/ebook/cover.* pour trouver la catégorie.
    """
    jpeg_root = os.path.join(SOURCE_ROOT, "en", "jpeg")
    for cat in ("lw", "gs", "fw"):
        base = os.path.join(jpeg_root, cat, code, "skins", "ebook")
        for filename in ("cover.jpg", "cover.jpeg", "cover.png"):
            if os.path.isfile(os.path.join(base, filename)):
                return cat
    return "fw"

def _clean_snippet(text: str, max_len: int = 900) -> str:
    t = re.sub(r"\s+", " ", strip_tags(text)).strip()
    if len(t) <= max_len:
        return t
    # coupe sur une limite de phrase/mot pour un rendu propre
    cut = t.rfind(". ", 0, max_len)
    if cut == -1:
        cut = t.rfind(" ", 0, max_len)
    if cut == -1:
        cut = max_len
    return t[:cut].rstrip() + "…"

import json  # en haut du script

def insert_combats(conn: sqlite3.Connection, book_id: int, book: Dict, sec_id_to_rowid: Dict[str, int]) -> None:
    cur = conn.cursor()
    for cb in book.get("combats", []):
        sid = cb["section"]
        section_rowid = sec_id_to_rowid.get(sid)
        if not section_rowid:
            continue

        cur.execute(
            "INSERT INTO combats(book_id, section_id, note) VALUES (?, ?, ?)",
            (book_id, section_rowid, None)
        )
        combat_id = cur.lastrowid

        for e in cb["enemies"]:
            cur.execute(
                "INSERT INTO combat_enemies(combat_id, enemy_index, name, cs, ep, extra_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    combat_id,
                    e.get("index", 0),
                    e.get("name"),
                    e.get("cs"),
                    e.get("ep"),
                    json.dumps(e.get("extra")) if e.get("extra") else None
                )
            )
    conn.commit()


# ---------- Programme principal ----------

def main():
    if not os.path.isdir(SOURCE_ROOT):
        print(f"[ERREUR] Dossier source introuvable : {SOURCE_ROOT}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)

        xml_dir = os.path.join(SOURCE_ROOT, "en", "xml")
        xml_files = sorted(glob(os.path.join(xml_dir, "*.xml")))
        if not xml_files:
            print(f"[ATTENTION] Aucun XML trouvé sous {xml_dir}", file=sys.stderr)

        for xml_path in xml_files:
            code = os.path.splitext(os.path.basename(xml_path))[0].lower()

            # ne traiter que les codes commençant par un chiffre
            if not re.match(r"^\d", code):
                continue
            if ONLY_CODES and code not in ONLY_CODES:
                continue

            category = find_category_from_cover(code)

            book = parse_book_from_file(xml_path)
            if not book["lang"].startswith(LANG_FILTER_PREFIX):
                continue

            book_id = upsert_book(conn, book["code"], book["title"], book["lang"], category, book.get("synopsis"))
            insert_sections_links_images(conn, book_id, book)

            print(f"✓ Importé {book['code']} — {book['title']} ({book['lang']}) [{category}] "
                  f"→ sections: {len(book['sections'])}, liens: {len(book['links'])}, images: {len(book['images'])}")
        print(f"\nBase créée: {DB_PATH}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
