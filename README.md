# README — Lone Wolf (Project Aon) • Site Flask

Un mini-site Flask pour parcourir les livres Lone Wolf / Grey Star / Freeway Warrior (Project Aon) : page d’accueil moderne par catégories, fiche livre (couverture + synopsis), lecture des sections (texte, illustrations, choix cliquables) et système de combat tour par tour.


## ✅ Prérequis

- Python 3.10+ (3.11 recommandé)

- Modules Python :

    - Flask


Installation de Flask :

``` bash
pip install Flask
```



## 📁 Arborescence attendue

Placez tout à la racine du projet :
```
./
├─ app.py
├─ build_database.py             
├─ data/
│   └─ lonewolf.db               # sera générée
├─ project-aon-master/           # archive Project Aon DÉZIPPÉE
│   ├─ common/...
│   └─ en/...                
├─ static/
│   └─ style.css
└─ templates/
    ├─ index.html
    ├─ book.html
    └─ play.html
    └─ combat.html
```

**Important :** les XML doivent se trouver dans project-aon-master/en/xml/.
Les images (illustrations/couvertures) sont cherchées en priorité dans **png**, puis **jpeg**, puis **gif**.

## 🧱 1) Générer la base SQLite

Le script analyse les XML et construit ./data/lonewolf.db.

```
# Linux / macOS
python build_database.py

# Windows (PowerShell)
python .\build_database.py
```

Le script :

- importe les livres EN (titre, synopsis, catégories),
- parse les sections, liens de choix, illustrations,
- détecte les combats (ennemis CS/EP) lorsque présents,
- enregistre tout dans la base SQLite.

La base est créée dans : ./data/lonewolf.db.

## 🚀 2) Lancer le site Flask
```
# Linux / macOS
python app.py

# Windows (PowerShell)
python .\app.py
```

Par défaut, le site écoute sur :

```
http://127.0.0.1:5000 
```

## 🧭 3) Utilisation

- Accueil : les livres sont affichés par catégories
lw = Lone Wolf, gs = Grey Star, fw = Freeway Warrior.

- Fiche livre : couverture grand format + synopsis + bouton “Commencer l’aventure”.

- Lecture : texte de la section, illustrations (si présentes), choix empilés à gauche.

- Combat : lorsqu’une section comporte un combat, un encart “⚔️ Combat” apparaît → bouton Engager le combat :

    - formulaire de départ (vos CS/EP + ceux de l’ennemi préremplis si trouvés),

    - résolution tour par tour avec bouton “Tour suivant”, barres d’EP, journal des rounds,

    - fin → Continuer l’histoire (retour à la lecture).


## 🔧 4) Configuration rapide

**Port / Host :** modifiez la dernière ligne de app.py si besoin :

```
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
```

**Chemins :**

- Le script DB suppose ./project-aon-master et crée ./data/lonewolf.db.

- app.py sert les images depuis project-aon-master/en/{png,jpeg,gif}/....


## 🙏 Crédits / Licence

- Textes et images des livres : Project Aon — respectez leurs licences et mentions.

- Ce projet n’est pas affilié à Project Aon / Joe Dever ; usage à but éducatif/démonstration.

> Bon jeu ! 🎲