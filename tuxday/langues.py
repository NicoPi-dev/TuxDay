"""Chargement des fichiers de langue (data/lang/*.json).

Ajouter une langue = déposer un fichier xx.json dans data/lang/.
Aucune ligne de code à modifier : les langues sont découvertes automatiquement.
"""

import json
import os
from pathlib import Path

from tuxday import DOSSIER_LANGUES

# Langue de secours si la langue du système n'a pas de fichier.
LANGUE_PAR_DEFAUT = "en"

# Langue de référence : les explications et libellés manquants sont pris ici.
LANGUE_REFERENCE = "fr"


def langues_disponibles(dossier: Path = DOSSIER_LANGUES) -> list[str]:
    """Renvoie la liste triée des codes de langue trouvés (ex. ['en', 'fr'])."""
    # p.stem est le nom du fichier sans son extension : "fr.json" -> "fr".
    return sorted(p.stem for p in Path(dossier).glob("*.json"))


def langue_systeme(disponibles: list[str], environ=None) -> str:
    """Devine la langue à partir de la variable LANG (ex. 'fr_FR.UTF-8' -> 'fr').

    Si aucun fichier n'existe pour cette langue, on prend l'anglais.
    """
    if environ is None:
        environ = os.environ
    valeur = environ.get("LANG", "")
    # On garde les lettres avant le premier '_' ou '.' : "fr_FR.UTF-8" -> "fr".
    code = valeur.split(".")[0].split("_")[0].lower()
    if code in disponibles:
        return code
    if LANGUE_PAR_DEFAUT in disponibles:
        return LANGUE_PAR_DEFAUT
    # Cas extrême : ni la langue du système ni l'anglais. On prend la première.
    return disponibles[0] if disponibles else LANGUE_PAR_DEFAUT


def ordre_affichage(disponibles: list[str], environ=None) -> list[str]:
    """Les langues dans l'ordre des boutons : celle du système d'abord, puis les autres."""
    premiere = langue_systeme(disponibles, environ)
    return [premiere] + [code for code in disponibles if code != premiere]


def choisir_langue(forcee: str | None, enregistree: str | None,
                   disponibles: list[str], environ=None) -> str:
    """Choisit la langue à afficher, par ordre de priorité :

    1. celle passée en ligne de commande (--lang) ;
    2. celle enregistrée dans config.json ;
    3. celle du système.
    """
    for candidate in (forcee, enregistree):
        if candidate and candidate in disponibles:
            return candidate
    return langue_systeme(disponibles, environ)


def _lire_json(chemin: Path) -> dict:
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def _fusionner(base: dict, dessus: dict) -> dict:
    """Copie de `base` où les valeurs de `dessus` remplacent celles de `base`.

    Les sous-dictionnaires (comme "themes" ou "levels") sont fusionnés aussi :
    une clé absente de `dessus` garde la valeur de `base`.
    """
    resultat = dict(base)
    for cle, valeur in dessus.items():
        if isinstance(valeur, dict) and isinstance(base.get(cle), dict):
            resultat[cle] = _fusionner(base[cle], valeur)
        else:
            resultat[cle] = valeur
    return resultat


def charger_langue(code: str, dossier: Path = DOSSIER_LANGUES) -> dict:
    """Charge les libellés de la langue `code`.

    Les libellés absents de ce fichier sont complétés par le français.
    """
    dossier = Path(dossier)
    reference = dossier / f"{LANGUE_REFERENCE}.json"
    textes = _lire_json(reference) if reference.exists() else {}
    if code != LANGUE_REFERENCE:
        textes = _fusionner(textes, _lire_json(dossier / f"{code}.json"))
    return textes


def explication(textes_par_langue: dict, code: str) -> str:
    """Renvoie l'explication dans la langue `code`, sinon en français."""
    return textes_par_langue.get(code) or textes_par_langue.get(LANGUE_REFERENCE, "")
