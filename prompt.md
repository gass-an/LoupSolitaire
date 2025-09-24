Entièrement fait avec le modèle GPT-5 de openAi, voici les prompts qui m'ont le plus aidé :

à savoir que tous les prompt son dans la même discussion et donc qu'il garde le contexte d'un prompt à l'autre

Prompt 1 : 
---

Tu es un developpeur : on a fourni une archive (ici légérement simplifié) contenant différents livres à choix / du texte au format xml et des illustrations référencées dans les xml égalements (et via l'architechture du zip). la mission donnée est la suivante :
Après avoir analysé en profondeur la structure des répertoires fournis et en utilisant une IA générative de votre choix et l’archive fournie, vous devrez générer un site dynamique en flask (Python) pour afficher dans un navigateur, l’ensemble des pages et liens des livres. Un bonus sera ajouté à l’ajout de la gestion du héros.
L’utilisation des scripts PERL inclus n’est pas l’attendu de ce devoir, ils peuvent toutefois être utile à votre IA générative pour comprendre la structure XML des fichiers fournis. Pour information, les scripts servent à générer une page par section, ce qui n’est pas l’attendu.

```
1. Génération de la base de données des livres dont vous êtes le héros série « Loup Solitaire »
Vous devrez demander à votre IA de générer l’ensemble des données permettant d’une part, d’avoir les contenus pour chaque livre, des sections et l’ensemble des liens cliquables depuis la section concernée. Vous devrez pour cela procéder avec l’aide de votre IA à une analyse des pertinente des fichiers disponibles. La langue fournie est l’anglais, l’espagnol est optionnel pour l’exercice. Des illustrations sont parfois jointes à la section affichée, il faudra que l’IA les inclût dans sa base. Le choix du système de base de données est libre, mais il doit être facile à installer et de type logiciel libre.

2. Génération du site
Une fois la base de données complète, vous devrez générer en flask, avec un css fait par l’IA donnant une touche de modernité, l’enchainement des livres en partant de la page « titre » et/ou « section 1 ». Pour aider votre IA, n’hésitez pas à lui indiquer des liens comme https://www.projectaon.org/en/xhtml/lw/01fftd/title.htm
Merci de bien faire attention aux adaptations CSS faites en fonction du contenu XML.

3. Passage au multilingue
Une fois la génération fonctionnelle, vous demanderez à votre IA d’adapter la base de données afin de prendre en compte plusieurs langues comme l’anglais et le français. Le site devra probablement être légèrement adapté.
Il faudra mettre en base la traduction des livres et permettre de choisir la langue que l’on souhaite à tout moment dans le site. Vous pourrez utiliser l’IA pour générer la traduction de chaque item de la base. Pour l’aider, vous pouvez lui proposer de regarder là : http://chg96.free.fr/loup-solitaire/jouable/lmdt/depart.htm

```

Concentre toi sur la partie 1 et donne moi un script en .py pour créer une database en SQLite qui pourra répondre au besoin ( a savoir utiliser le site pour jouer l'histoire, acceder aux liens pour changer de pages / afficher les images ect...)




Prompt 2 :
---

ok on va passer à la génération du site avec flask, concentre toi pour l'instant sur la page d'acceuil, il faudrait afficher les livres par catégorie : fw / gs / lw (lone wolf) donc trouve ce que signifie les autres et affiche les livres (4 par lignes) avec l'image du livre en gros et le titre clicable en dessous, l'image est disponible (par exemple : project-aon-master\en\jpeg\lw\01fftd\skins\ebook pour le premier livre de lone wolf ) 

je veux que le site ai un desing moderne ! 

j'attends que tu fournisse le app.py le style.css et le template pour l'acceuil du site (en html)



___
quelques petit prompt pour régler des soucis de chemin pour les couvertures...
___


Prompt 3 : (je lui ai également fourni le app.py ey le style.css actuel pour qu'il se souvienne à quelle étape j'en suis)
---

je souhaite maintenant, quand on clique sur un livre on arrive sur une page où la couverture est un peu plus grande et on affiche le synopsis, puis en bas de page il y a un bouton "commencer l'aventure" qui ne mène nulle part pour l'instant genere moi le template et modifie le app.py et le css si necessaire



Prompt 4 : (il a fait directement les modifications necessaires aux choix)
---
la base est-elle prête pour la suite : c'est a dire afficher le contenu d'une section (texte et illustration) et afficher les choix que le joueur peut faire ? (go to 235 ...)


Prompt 5 : (je lui redonne aussi le app.py pour qu'il apporte les modifications necessaires)
---

on avance bien, maintenant je souhaite afficher les ilustrations de chaque section (s'il y en a une), noramlement la db possède le nom des images de chaque section, il faudrait d'abourd aller chercher dans le dossier png, si pas trouvé, dans le dossier jpeg, ect... en se souvenant de l'architecture des dossiers