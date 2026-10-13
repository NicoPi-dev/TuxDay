"""TuxDay : chaque jour, 4 commandes à taper pour apprendre Linux et Python."""

from pathlib import Path

__version__ = "0.1.0"

# Dossier racine du projet (celui qui contient data/, assets/, tuxday/...).
RACINE = Path(__file__).resolve().parent.parent

# Fichiers de données fournis avec TuxDay.
DOSSIER_DATA = RACINE / "data"
FICHIER_COMMANDES = DOSSIER_DATA / "commands.json"
DOSSIER_LANGUES = DOSSIER_DATA / "lang"

# Logo : tuxday.svg (grandes tailles) et tuxday-small.svg (simplifié, pour 16 à 32 px).
DOSSIER_ASSETS = RACINE / "assets"
