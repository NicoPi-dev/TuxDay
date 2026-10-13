#!/usr/bin/env bash
# install.sh — installe TuxDay pour l'utilisateur courant (aucun sudo).
#
#   1. vérifie que Python 3 et PySide6 sont présents ;
#   2. sauvegarde ~/.config/kwinrulesrc, puis crée la règle de fenêtre KWin « tuxday » ;
#   3. demande à KWin de recharger ses règles ;
#   4. installe le logo dans le thème d'icônes ~/.local/share/icons/hicolor ;
#   5. crée le lancement automatique ~/.config/autostart/tuxday.desktop ;
#   6. ajoute TuxDay au menu des applications (catégorie Éducation) :
#      ~/.local/share/applications/tuxday.desktop.
#
# TuxDay reste dans ce dossier : le démarrage automatique le lance d'ici.
#
# Position de la fenêtre (coin haut gauche, en pixels) :
#   - par défaut en 40,56, en haut à gauche de l'écran ;
#   - ou là où vous voulez :  ./install.sh --position X,Y
#
# On peut relancer ce script sans risque : il remplace simplement la règle TuxDay.

set -euo pipefail   # arrêt à la première erreur ou variable inconnue

# --- Réglages -----------------------------------------------------------------

DOSSIER="$(cd "$(dirname "$0")" && pwd)"   # dossier du projet
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"
REGLES="$CONFIG/kwinrulesrc"
GROUPE="tuxday"                  # nom de la section de la règle dans kwinrulesrc
AUTOSTART="$CONFIG/autostart/tuxday.desktop"
MENU="${XDG_DATA_HOME:-$HOME/.local/share}/applications/tuxday.desktop"
ICONES="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"   # thème d'icônes de base
DELAI=3                          # secondes d'attente au démarrage de la session
POSITION="40,56"                 # position par défaut : en haut à gauche

# --- Options ------------------------------------------------------------------

while [ $# -gt 0 ]; do
    case "$1" in
        --position) POSITION="${2:-}"; shift 2 ;;
        -h|--help)  sed -n '2,16p' "$0"; exit 0 ;;
        *) echo "Option inconnue : $1 (voir --help)" >&2; exit 1 ;;
    esac
done

# --- 1. Vérifications ---------------------------------------------------------

echo "== Vérifications"
command -v python3 >/dev/null || { echo "python3 est introuvable." >&2; exit 1; }
python3 -c "import PySide6" 2>/dev/null || {
    echo "PySide6 manque. Sous Fedora : sudo dnf install python3-pyside6" >&2; exit 1; }
for outil in kreadconfig6 kwriteconfig6; do
    command -v "$outil" >/dev/null || { echo "$outil est introuvable (KDE Plasma 6 requis)." >&2; exit 1; }
done
polices="$(fc-list : family 2>/dev/null || true)"
if ! grep -qi "JetBrains Mono" <<< "$polices"; then
    echo "Info : police JetBrains Mono absente, TuxDay utilisera la police monospace du système."
    echo "       (Fedora : sudo dnf install jetbrains-mono-fonts)"
fi

# --- 2. Position de la fenêtre ------------------------------------------------

[[ "$POSITION" =~ ^[0-9]+,[0-9]+$ ]] || { echo "Position invalide : $POSITION (attendu X,Y)" >&2; exit 1; }
echo "== TuxDay ira en $POSITION"

# --- 3. Règle KWin ------------------------------------------------------------

# Sauvegarde datée avant toute modification.
if [ -f "$REGLES" ]; then
    sauvegarde="$REGLES.bak-$(date +%Y%m%d-%H%M%S)"
    cp -p "$REGLES" "$sauvegarde"
    echo "== Sauvegarde : $sauvegarde"
fi

ecrire() { kwriteconfig6 --file "$REGLES" --group "$GROUPE" --key "$1" "$2"; }

echo "== Règle KWin « $GROUPE »"
ecrire Description   "TuxDay"
ecrire wmclass       "tuxday"     # classe de la fenêtre...
ecrire wmclassmatch  1            # ... en correspondance exacte : aucune autre fenêtre visée
ecrire position      "$POSITION"; ecrire positionrule     2   # 2 = forcer
ecrire below         true;        ecrire belowrule        2   # sous les autres fenêtres
ecrire skiptaskbar   true;        ecrire skiptaskbarrule  2   # pas dans la barre des tâches
ecrire skippager     true;        ecrire skippagerrule    2   # pas dans le sélecteur de bureaux
ecrire skipswitcher  true;        ecrire skipswitcherrule 2   # pas dans Alt+Tab
ecrire noborder      true;        ecrire noborderrule     2   # pas de barre de titre

# Ajoute « tuxday » à la liste des règles de [General] (une seule fois).
liste="$(kreadconfig6 --file "$REGLES" --group General --key rules)"
if [[ ",$liste," != *",$GROUPE,"* ]]; then
    liste="${liste:+$liste,}$GROUPE"
fi
kwriteconfig6 --file "$REGLES" --group General --key rules "$liste"
# count = nombre de règles de la liste.
IFS=',' read -ra noms <<< "$liste"
kwriteconfig6 --file "$REGLES" --group General --key count "${#noms[@]}"

# Demande à KWin de relire ses règles.
if dbus-send --session --print-reply --dest=org.kde.KWin /KWin org.kde.KWin.reconfigure >/dev/null 2>&1; then
    echo "== KWin a rechargé sa configuration"
else
    echo "Attention : KWin n'a pas pu être rechargé ; la règle s'appliquera à la prochaine session."
fi

# --- 4. Icône -----------------------------------------------------------------

# Le thème « hicolor » est celui où toutes les applications déposent leur icône.
# Une version vectorielle (scalable) + des PNG pour chaque taille : le bureau
# choisit la mieux adaptée. Les .desktop la désignent par son nom : Icon=tuxday.
echo "== Icône : $ICONES"
install -Dm644 "$DOSSIER/assets/tuxday.svg" "$ICONES/scalable/apps/tuxday.svg"
for png in "$DOSSIER"/assets/png/tuxday-*.png; do
    taille="$(basename "$png" .png)"   # « tuxday-48 »
    taille="${taille#tuxday-}"         # « 48 »
    install -Dm644 "$png" "$ICONES/${taille}x${taille}/apps/tuxday.png"
done
# Met à jour le cache des icônes (s'il existe ; -t : même sans fichier index.theme).
if command -v gtk-update-icon-cache >/dev/null; then
    gtk-update-icon-cache -f -t "$ICONES" >/dev/null 2>&1 || true
fi

# --- 5. Démarrage automatique -------------------------------------------------

# Le délai laisse le bureau finir de s'installer (panneaux, fenêtres lancées dans
# la même phase du démarrage de Plasma) avant d'ouvrir TuxDay.
echo "== Démarrage automatique : $AUTOSTART"
mkdir -p "$(dirname "$AUTOSTART")"
cat > "$AUTOSTART" <<EOF
[Desktop Entry]
Type=Application
Name=TuxDay
Comment=4 commandes par jour pour apprendre Linux
Icon=tuxday
Path=$DOSSIER
Exec=sh -c "sleep $DELAI; exec python3 -m tuxday"
Terminal=false
NoDisplay=true
X-KDE-autostart-phase=2
EOF
if command -v desktop-file-validate >/dev/null; then
    desktop-file-validate "$AUTOSTART"
fi

# --- 6. Menu des applications -------------------------------------------------

# Ce fichier fait apparaître TuxDay dans le menu KDE. Son nom, « tuxday.desktop »,
# correspond à QGuiApplication.setDesktopFileName("tuxday") : le système fait ainsi
# le lien entre la fenêtre et l'application (sans lui, le portail XDG répond
# « Could not register app ID: App info not found for 'tuxday' »).
echo "== Menu des applications : $MENU"
mkdir -p "$(dirname "$MENU")"
cat > "$MENU" <<EOF
[Desktop Entry]
Type=Application
Name=TuxDay
GenericName=Learn Linux
GenericName[fr]=Apprendre Linux
Comment=4 commands a day to learn Linux
Comment[fr]=4 commandes par jour pour apprendre Linux
Path=$DOSSIER
Exec=python3 -m tuxday
Icon=tuxday
Terminal=false
Categories=Education;ComputerScience;
Keywords=linux;shell;python;terminal;learn;apprendre;commandes;
StartupWMClass=tuxday
EOF
if command -v desktop-file-validate >/dev/null; then
    desktop-file-validate "$MENU"
fi
# Met à jour le cache des menus pour que TuxDay y apparaisse tout de suite.
if command -v kbuildsycoca6 >/dev/null; then
    kbuildsycoca6 >/dev/null 2>&1 || true
fi

echo
echo "TuxDay est installé. Il s'ouvrira à la prochaine connexion."
echo "Pour l'essayer tout de suite : cd \"$DOSSIER\" && python3 -m tuxday"
echo "Pour tout retirer : \"$DOSSIER/uninstall.sh\""
