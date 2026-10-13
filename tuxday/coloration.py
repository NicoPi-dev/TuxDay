"""Coloration des commandes et des explications (produit du HTML pour Qt).

Séparé de fenetre.py pour pouvoir être testé sans interface graphique.
"""

import html
import re

# Couleurs de la maquette.
CYAN = "#7fd3f5"
JAUNE = "#f7e08a"
BLANC = "#f2f3f8"

# Séparateurs après lesquels un nouveau nom de commande commence.
SEPARATEURS = ("|", "||", "&&", ";")


def decouper(cmd: str) -> list[tuple[str, str]]:
    """Découpe une ligne de commande en morceaux (genre, texte).

    genre vaut "espace", "operateur" ou "mot". Les guillemets sont respectés :
    un | entre guillemets fait partie du mot, ce n'est pas un pipe.
    """
    morceaux = []
    i = 0
    while i < len(cmd):
        c = cmd[i]
        if c.isspace():
            j = i
            while j < len(cmd) and cmd[j].isspace():
                j += 1
            morceaux.append(("espace", cmd[i:j]))
            i = j
        elif cmd.startswith(("||", "&&"), i):
            morceaux.append(("operateur", cmd[i:i + 2]))
            i += 2
        elif c in "|;":
            morceaux.append(("operateur", c))
            i += 1
        else:
            # Un mot : on avance jusqu'à un espace ou un opérateur hors guillemets.
            j = i
            guillemet = None
            while j < len(cmd):
                d = cmd[j]
                if guillemet:
                    if d == "\\" and guillemet == '"':
                        j += 1          # caractère échappé : on le saute
                    elif d == guillemet:
                        guillemet = None
                elif d in "'\"":
                    guillemet = d
                elif d == "\\":
                    j += 1
                elif d.isspace() or d in "|;" or cmd.startswith("&&", j):
                    break
                j += 1
            morceaux.append(("mot", cmd[i:j]))
            i = j
    return morceaux


def couleurs_commande(cmd: str) -> list[tuple[str, str]]:
    """Associe une couleur à chaque morceau de la commande.

    Premier mot (et premier mot après |, ||, &&, ;) : jaune.
    Mot qui commence par - : cyan. Le reste : blanc.
    """
    resultat = []
    debut_de_commande = True
    for genre, texte in decouper(cmd):
        if genre == "espace":
            resultat.append((texte, BLANC))
        elif genre == "operateur":
            resultat.append((texte, BLANC))
            debut_de_commande = texte in SEPARATEURS
        elif debut_de_commande:
            resultat.append((texte, JAUNE))
            debut_de_commande = False
        elif texte.startswith("-"):
            resultat.append((texte, CYAN))
        else:
            resultat.append((texte, BLANC))
    return resultat


def noms_de_commandes(cmd: str) -> set[str]:
    """Les mots colorés en jaune dans la commande (ex. {'echo', 'rev'})."""
    return {texte for texte, couleur in couleurs_commande(cmd) if couleur == JAUNE}


def _span(texte: str, couleur: str) -> str:
    return f'<span style="color:{couleur}">{html.escape(texte, quote=False)}</span>'


def html_commande(cmd: str) -> str:
    """La commande colorée, en HTML. Les espaces sont gardés tels quels."""
    morceaux = []
    for texte, couleur in couleurs_commande(cmd):
        # Plusieurs espaces de suite : on les garde visibles (insécables sauf le dernier).
        if texte.isspace():
            morceaux.append("&nbsp;" * (len(texte) - 1) + " ")
        else:
            morceaux.append(_span(texte, couleur))
    return "".join(morceaux)


def _couleur_mot_cle(mot: str, noms: set[str]) -> str:
    if mot.startswith("-"):
        return CYAN
    if mot in noms:
        return JAUNE
    return BLANC


def html_explication(explication: str, cmd: str) -> str:
    """L'explication en HTML : chaque `mot-clé` est coloré, sans les accents graves.

    Un mot-clé de plusieurs mots (ex. `python3 -c`) est coloré mot par mot.
    Le texte normal n'a pas de couleur ici : il prend celle du widget (gris lavande).
    """
    noms = noms_de_commandes(cmd)
    resultat = []
    # re.split avec des parenthèses garde les mots-clés : les indices impairs.
    for i, partie in enumerate(re.split(r"`([^`]+)`", explication)):
        if i % 2 == 0:
            resultat.append(html.escape(partie, quote=False))
        elif partie in noms or " " not in partie:
            resultat.append(_span(partie, _couleur_mot_cle(partie, noms)))
        else:
            resultat.append(" ".join(_span(m, _couleur_mot_cle(m, noms))
                                     for m in partie.split(" ")))
    return "".join(resultat)
