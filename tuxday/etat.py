"""Lecture et écriture de l'état et de la configuration.

Emplacements (norme XDG) :
  état          : $XDG_STATE_HOME/tuxday/state.json   (défaut ~/.local/state)
  configuration : $XDG_CONFIG_HOME/tuxday/config.json (défaut ~/.config)

L'état contient :
  date          : date de la série du jour, ex. "2026-10-13"
  niveau        : niveau de la série du jour (1 à 4)
  niveau_veille : niveau du jour précédent
  serie         : identifiants des 4 commandes du jour
  vus           : identifiants de toutes les commandes déjà montrées
"""

import fcntl
import json
import os
from pathlib import Path

# Dossier où les commandes du jour créent leurs fichiers.
DOSSIER_ESSAI = Path.home() / "essai_linux"


def _dossier_xdg(variable: str, defaut: str, environ=None) -> Path:
    """Dossier XDG : la variable d'environnement si elle est définie, sinon le défaut."""
    if environ is None:
        environ = os.environ
    base = environ.get(variable) or os.path.expanduser(defaut)
    return Path(base) / "tuxday"


def fichier_etat(environ=None) -> Path:
    return _dossier_xdg("XDG_STATE_HOME", "~/.local/state", environ) / "state.json"


def fichier_config(environ=None) -> Path:
    return _dossier_xdg("XDG_CONFIG_HOME", "~/.config", environ) / "config.json"


def etat_vide() -> dict:
    """État de départ, quand TuxDay n'a encore jamais tourné."""
    return {"date": None, "niveau": None, "niveau_veille": None, "serie": [], "vus": []}


def _lire(chemin: Path) -> dict:
    """Lit un fichier JSON. Renvoie {} s'il n'existe pas ou s'il est abîmé."""
    try:
        with open(chemin, encoding="utf-8") as f:
            donnees = json.load(f)
        return donnees if isinstance(donnees, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _ecrire(chemin: Path, donnees: dict) -> None:
    """Écrit un fichier JSON sans risque de le laisser à moitié écrit.

    On écrit d'abord dans un fichier temporaire, puis on le renomme :
    le renommage est instantané, donc le fichier est soit l'ancien, soit le nouveau.
    """
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(".tmp")
    with open(temporaire, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)
    os.replace(temporaire, chemin)


def charger_etat(chemin: Path | None = None) -> dict:
    """Charge l'état ; les clés manquantes prennent leur valeur de départ."""
    etat = etat_vide()
    etat.update(_lire(chemin or fichier_etat()))
    return etat


def enregistrer_etat(etat: dict, chemin: Path | None = None) -> None:
    _ecrire(chemin or fichier_etat(), etat)


def effacer_etat(chemin: Path | None = None) -> None:
    """Supprime le fichier d'état (option --reset)."""
    (chemin or fichier_etat()).unlink(missing_ok=True)


def charger_config(chemin: Path | None = None) -> dict:
    return _lire(chemin or fichier_config())


def enregistrer_config(config: dict, chemin: Path | None = None) -> None:
    _ecrire(chemin or fichier_config(), config)


def lire_echelle(config: dict, defaut: float) -> float:
    """Échelle de la fenêtre (clé "echelle" de config.json).

    Une valeur absente, mal écrite ou hors de 0,5 à 3 est remplacée par `defaut`.
    """
    valeur = config.get("echelle", defaut)
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)):
        return defaut
    if not 0.5 <= valeur <= 3:
        return defaut
    return float(valeur)


def fichier_verrou(environ=None) -> Path:
    """Fichier verrou d'une instance : dans $XDG_RUNTIME_DIR (vidé à chaque démarrage).

    Sans XDG_RUNTIME_DIR, on se rabat sur le dossier de l'état.
    """
    if environ is None:
        environ = os.environ
    if environ.get("XDG_RUNTIME_DIR"):
        return Path(environ["XDG_RUNTIME_DIR"]) / "tuxday.lock"
    return fichier_etat(environ).with_name("tuxday.lock")


def prendre_verrou(chemin: Path | None = None):
    """Empêche TuxDay de tourner deux fois.

    Renvoie le fichier ouvert si on est le seul TuxDay (il faut le garder ouvert
    tant que la fenêtre vit), ou None si un autre TuxDay tient déjà le verrou.
    Le système libère le verrou tout seul quand le programme s'arrête, même en cas de plantage.
    """
    chemin = Path(chemin or fichier_verrou())
    chemin.parent.mkdir(parents=True, exist_ok=True)
    fichier = open(chemin, "w")
    try:
        # LOCK_EX : verrou exclusif ; LOCK_NB : ne pas attendre s'il est déjà pris.
        fcntl.flock(fichier, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fichier.close()
        return None
    return fichier


def creer_dossier_essai(dossier: Path = DOSSIER_ESSAI) -> None:
    """Crée ~/essai_linux s'il n'existe pas (les commandes du jour y travaillent)."""
    Path(dossier).mkdir(parents=True, exist_ok=True)
