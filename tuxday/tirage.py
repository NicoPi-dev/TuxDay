"""Choix du niveau du jour et des 4 commandes.

Règles :
  1. Une série par jour : si l'état a déjà la série d'aujourd'hui, on la garde.
  2. Nouveau jour : niveau tiré au hasard parmi les 3 différents de la veille.
  3. Dans ce niveau : 2 commandes shell puis 2 commandes Python, jamais vues,
     dont les prérequis (`requires`) sont présents, avec au plus une paire par bloc.
  4. Plus assez de commandes jamais vues pour un niveau et un type ?
     On oublie les commandes vues de ce niveau et de ce type seulement, et on recommence.
  5. On enregistre la série et on ajoute ses identifiants aux commandes vues.

Pour les tests, la date, le hasard (`rng`) et la vérification des prérequis
(`verifier`) peuvent être fournis de l'extérieur.
"""

import datetime
import glob
import importlib.util
import json
import os
import random
import shutil
from pathlib import Path

from tuxday import FICHIER_COMMANDES

NIVEAUX = (1, 2, 3, 4)
TYPES = ("shell", "python")   # dans l'ordre d'affichage
PAR_BLOC = 2                  # commandes par bloc


class TirageImpossible(Exception):
    """Levée quand un niveau n'a vraiment pas assez de commandes utilisables."""


def charger_commandes(fichier: Path = FICHIER_COMMANDES) -> list[dict]:
    """Lit la bibliothèque et renvoie la liste des commandes."""
    with open(fichier, encoding="utf-8") as f:
        return json.load(f)["entries"]


# --- Prérequis -------------------------------------------------------------

def exigence_satisfaite(exigence: str) -> bool:
    """Vérifie un prérequis sur cette machine.

    "path:..."  -> un chemin (jokers * acceptés) doit exister ;
    "py:..."    -> un module Python doit être installé ;
    sinon       -> un programme doit être trouvable dans le PATH.
    """
    if exigence.startswith("path:"):
        motif = os.path.expanduser(exigence[len("path:"):])
        return bool(glob.glob(motif))
    if exigence.startswith("py:"):
        try:
            return importlib.util.find_spec(exigence[len("py:"):]) is not None
        except (ImportError, ValueError):
            return False
    return shutil.which(exigence) is not None


def prerequis_ok(entree: dict, verifier=exigence_satisfaite) -> bool:
    """Vrai si tous les `requires` de la commande sont satisfaits."""
    return all(verifier(e) for e in entree.get("requires", []))


# --- Tirage ----------------------------------------------------------------

def tirer_niveau(niveau_veille: int | None, rng: random.Random) -> int:
    """Niveau au hasard, toujours différent de celui de la veille."""
    possibles = [n for n in NIVEAUX if n != niveau_veille]
    return rng.choice(possibles)


def _choisir_bloc(candidates: list[dict], rng: random.Random) -> list[dict] | None:
    """Choisit PAR_BLOC commandes parmi `candidates`, avec au plus une paire.

    Renvoie None s'il n'y en a pas assez.
    """
    melange = list(candidates)
    rng.shuffle(melange)
    bloc = []
    paire_prise = False
    for entree in melange:
        est_paire = "inverse" in entree
        if est_paire and paire_prise:
            continue   # déjà une paire dans ce bloc : on passe
        bloc.append(entree)
        paire_prise = paire_prise or est_paire
        if len(bloc) == PAR_BLOC:
            return bloc
    return None


def tirer_bloc(entrees: list[dict], niveau: int, type_: str, vus: set[str],
               rng: random.Random, verifier=exigence_satisfaite) -> list[dict]:
    """Tire un bloc (shell ou python). Modifie `vus` si un oubli est nécessaire (règle 4)."""
    # Commandes de ce niveau et de ce type utilisables sur cette machine.
    utilisables = [e for e in entrees
                   if e["level"] == niveau and e["type"] == type_ and prerequis_ok(e, verifier)]

    bloc = _choisir_bloc([e for e in utilisables if e["id"] not in vus], rng)
    if bloc is None:
        # Règle 4 : on oublie les commandes vues de ce niveau et de ce type uniquement.
        ids_du_groupe = {e["id"] for e in entrees if e["level"] == niveau and e["type"] == type_}
        vus -= ids_du_groupe
        bloc = _choisir_bloc(utilisables, rng)
    if bloc is None:
        raise TirageImpossible(f"niveau {niveau}, type {type_} : pas assez de commandes")
    return bloc


def serie_du_jour(etat: dict, entrees: list[dict], aujourdhui: datetime.date,
                  rng: random.Random | None = None, verifier=exigence_satisfaite,
                  niveau_force: int | None = None) -> list[dict]:
    """Renvoie les 4 commandes du jour et met `etat` à jour (sans l'enregistrer sur disque).

    `niveau_force` (option --niveau) impose le niveau et provoque un nouveau tirage
    si la série enregistrée n'est pas de ce niveau.
    """
    rng = rng or random.Random()
    par_id = {e["id"]: e for e in entrees}
    date_texte = aujourdhui.isoformat()

    # Règle 1 : même jour -> même série (si elle existe encore dans la bibliothèque).
    meme_jour = etat.get("date") == date_texte
    if (meme_jour and etat.get("serie")
            and all(i in par_id for i in etat["serie"])
            and niveau_force in (None, etat.get("niveau"))):
        return [par_id[i] for i in etat["serie"]]

    # Règle 2 : le niveau de la dernière série devient le niveau de la veille.
    # (Si on refait un tirage le même jour, la veille ne change pas.)
    if not meme_jour:
        etat["niveau_veille"] = etat.get("niveau")
    niveau = niveau_force or tirer_niveau(etat.get("niveau_veille"), rng)

    # Règle 3 et 4 : un bloc shell puis un bloc python.
    vus = set(etat.get("vus", []))
    serie = []
    for type_ in TYPES:
        serie += tirer_bloc(entrees, niveau, type_, vus, rng, verifier)

    # Règle 5 : on mémorise.
    vus.update(e["id"] for e in serie)
    etat["date"] = date_texte
    etat["niveau"] = niveau
    etat["serie"] = [e["id"] for e in serie]
    etat["vus"] = sorted(vus)
    return serie
