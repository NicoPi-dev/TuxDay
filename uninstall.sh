#!/usr/bin/env bash
# uninstall.sh — retire TuxDay proprement.
#
#   - la règle de fenêtre KWin « tuxday » (et elle seule ; kwinrulesrc est sauvegardé avant) ;
#   - le démarrage automatique ~/.config/autostart/tuxday.desktop ;
#   - l'entrée du menu ~/.local/share/applications/tuxday.desktop ;
#   - les icônes tuxday de ~/.local/share/icons/hicolor ;
#   - l'état ~/.local/state/tuxday et la configuration ~/.config/tuxday.
#
# Ne touche PAS à ~/essai_linux (vos essais) ni au dossier du projet.
# Option : -y pour ne pas demander de confirmation.

set -euo pipefail

CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"
ETAT="${XDG_STATE_HOME:-$HOME/.local/state}/tuxday"
REGLES="$CONFIG/kwinrulesrc"
GROUPE="tuxday"
AUTOSTART="$CONFIG/autostart/tuxday.desktop"
MENU="${XDG_DATA_HOME:-$HOME/.local/share}/applications/tuxday.desktop"
ICONES="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"

# Les clés écrites par install.sh dans la section [tuxday].
CLES=(Description wmclass wmclassmatch position positionrule below belowrule
      skiptaskbar skiptaskbarrule skippager skippagerrule skipswitcher skipswitcherrule
      noborder noborderrule)

if [ "${1:-}" != "-y" ]; then
    echo "Seront supprimés :"
    echo "  - la règle KWin « $GROUPE » dans $REGLES"
    echo "  - $AUTOSTART"
    echo "  - $MENU"
    echo "  - les icônes tuxday dans $ICONES"
    echo "  - $ETAT"
    echo "  - $CONFIG/tuxday"
    echo "~/essai_linux est conservé."
    read -rp "Continuer ? [o/N] " reponse
    [[ "$reponse" =~ ^[oOyY]$ ]] || { echo "Annulé."; exit 0; }
fi

# --- TuxDay ouvert ? On le ferme. -----------------------------------------------
# « (^|/) » : lancé en « python3 » (terminal, autostart) ou « /usr/bin/python3 » (menu).
pkill -f "(^|/)python3 -m tuxday" 2>/dev/null || true

# --- Règle KWin -----------------------------------------------------------------
if [ -f "$REGLES" ]; then
    sauvegarde="$REGLES.bak-$(date +%Y%m%d-%H%M%S)"
    cp -p "$REGLES" "$sauvegarde"
    echo "== Sauvegarde : $sauvegarde"

    # Supprime chaque clé de [tuxday] ; une section vide disparaît du fichier.
    for cle in "${CLES[@]}"; do
        kwriteconfig6 --file "$REGLES" --group "$GROUPE" --key "$cle" --delete ""
    done

    # Retire « tuxday » de la liste des règles et recalcule count.
    liste="$(kreadconfig6 --file "$REGLES" --group General --key rules)"
    nouvelle=""
    IFS=',' read -ra noms <<< "$liste"
    total=0
    for nom in "${noms[@]}"; do
        if [ -z "$nom" ] || [ "$nom" = "$GROUPE" ]; then
            continue
        fi
        nouvelle="${nouvelle:+$nouvelle,}$nom"
        total=$((total + 1))
    done
    kwriteconfig6 --file "$REGLES" --group General --key rules "$nouvelle"
    kwriteconfig6 --file "$REGLES" --group General --key count "$total"
    echo "== Règle KWin « $GROUPE » retirée"

    dbus-send --session --print-reply --dest=org.kde.KWin /KWin org.kde.KWin.reconfigure \
        >/dev/null 2>&1 && echo "== KWin a rechargé sa configuration" || true
fi

# --- Démarrage automatique, état, configuration ---------------------------------
rm -f "$AUTOSTART"      && echo "== Supprimé : $AUTOSTART"
rm -f "$MENU"           && echo "== Supprimé : $MENU"
# Met à jour le cache des menus : TuxDay disparaît du menu KDE.
command -v kbuildsycoca6 >/dev/null && { kbuildsycoca6 >/dev/null 2>&1 || true; }

# --- Icônes ---------------------------------------------------------------------
# On retire uniquement les fichiers tuxday.* posés par install.sh.
if [ -d "$ICONES" ]; then
    find "$ICONES" -path "*/apps/tuxday.*" -type f -delete
    echo "== Icônes tuxday retirées de $ICONES"
    if [ -n "$(find "$ICONES" -type f ! -name icon-theme.cache -print -quit)" ]; then
        # D'autres applications ont des icônes ici : on régénère leur cache.
        command -v gtk-update-icon-cache >/dev/null && \
            { gtk-update-icon-cache -f -t "$ICONES" >/dev/null 2>&1 || true; }
    else
        # Il ne reste que le cache créé pour TuxDay : on le supprime.
        rm -f "$ICONES/icon-theme.cache"
    fi
    find "$ICONES" -type d -empty -delete   # dossiers devenus vides
    rmdir --ignore-fail-on-non-empty "$(dirname "$ICONES")" 2>/dev/null || true
fi

rm -rf "$ETAT"          && echo "== Supprimé : $ETAT"
rm -rf "$CONFIG/tuxday" && echo "== Supprimé : $CONFIG/tuxday"

echo
echo "TuxDay est désinstallé. ~/essai_linux et le dossier du projet sont intacts."
