"""Affichage de la fenêtre TuxDay avec PySide6.

La position, le « garder en dessous » et l'absence de barre des tâches sont
gérés par une règle KWin (voir install.sh) : sous Wayland, l'application
ne peut pas choisir elle-même sa place.
"""

import datetime
import html
import math

from PySide6.QtCore import Qt
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QPainter, QPen, QTextDocument,
                           QTextOption)
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)

from tuxday import coloration, langues

# --- Taille de l'ensemble ----------------------------------------------------

# Toutes les dimensions ci-dessous sont celles de la maquette (échelle 1).
# Elles sont multipliées par ECHELLE au moment de construire la fenêtre.
# La valeur réelle vient de la clé "echelle" de ~/.config/tuxday/config.json.
ECHELLE = 1.3


def definir_echelle(echelle: float) -> None:
    """Change l'échelle (à appeler avant de créer la fenêtre)."""
    global ECHELLE
    ECHELLE = echelle


def px(valeur: float) -> int:
    """Une dimension de la maquette, multipliée par l'échelle et arrondie au pixel.

    Une dimension non nulle fait toujours au moins 1 px (un trait reste visible).
    """
    if valeur == 0:
        return 0
    return max(1, round(valeur * ECHELLE))


# --- Valeurs de la maquette --------------------------------------------------

LARGEUR = 540
RAYON = 6
MARGE_COTES = 14
TRAIT = 1             # épaisseur des traits fins et des bordures
TRAIT_PAIRE_LARGE = 2  # épaisseur du trait jaune d'une paire
MARGE_PAIRE = 10      # espace entre le trait jaune et le texte
ESPACE = 9            # espace entre les lignes de contenu
RETRAIT = 14          # décalage des explications


def largeur_contenu() -> int:
    """Largeur disponible pour le texte : la fenêtre moins ses marges."""
    return px(LARGEUR) - 2 * px(MARGE_COTES)


def largeur_paire() -> int:
    """Largeur du texte dans une paire : moins le trait jaune et sa marge."""
    return largeur_contenu() - px(TRAIT_PAIRE_LARGE) - px(MARGE_PAIRE)


FOND = QColor(28, 30, 44, round(0.45 * 255))
BORDURE = QColor(255, 255, 255, round(0.14 * 255))

CYAN = "#7fd3f5"
JAUNE = "#f7e08a"
LAVANDE = "#bfc4d8"     # explications
GRIS = "#c4c8d6"        # intro, date, libellés secondaires
GRIS_INACTIF = "#a9aec2"
VERT = "#8fe3a8"
ORANGE = "#ffb27a"
TRAIT_SECTION = "rgba(127, 211, 245, 0.55)"
TRAIT_PAIRE = "rgba(247, 224, 138, 0.55)"
TRAIT_PIED = "rgba(255, 255, 255, 0.12)"

COULEURS_NIVEAUX = {1: "#8fe3a8", 2: "#7fd3f5", 3: "#ffb27a", 4: "#ff9db0"}


def famille_police() -> str:
    """JetBrains Mono si elle est installée, sinon la police monospace du système."""
    if "JetBrains Mono" in QFontDatabase.families():
        return "JetBrains Mono"
    return QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()


def police(taille: int, graisse=QFont.Weight.Normal) -> QFont:
    """Police de l'interface ; `taille` est celle de la maquette, en pixels."""
    f = QFont(famille_police())
    f.setPixelSize(px(taille))
    f.setWeight(graisse)
    return f


def etiquette(texte: str, couleur: str, taille: int = 12,
              graisse=QFont.Weight.Normal) -> QLabel:
    """Un QLabel simple, transparent, dans la couleur et la taille voulues."""
    label = QLabel(texte)
    label.setFont(police(taille, graisse))
    label.setStyleSheet(f"color: {couleur}; background: transparent;")
    return label


def trait_horizontal(couleur: str) -> QFrame:
    trait = QFrame()
    trait.setFixedHeight(px(TRAIT))
    trait.setStyleSheet(f"background: {couleur}; border: none;")
    return trait


class TexteRiche(QWidget):
    """Texte coloré (HTML) qui passe à la ligne dans une largeur connue d'avance.

    Contrairement à QLabel, il sait couper un mot très long n'importe où :
    les longues commandes passent donc à la ligne sans dépasser.
    La fenêtre a une largeur fixe, donc on connaît la largeur disponible
    dès la création : on en déduit tout de suite la hauteur du texte.
    """

    def __init__(self, html_texte: str, taille: int, couleur: str, largeur: int,
                 graisse=QFont.Weight.Normal, retrait: int = 0):
        super().__init__()
        self.retrait = retrait   # décalage vers la droite, en pixels (déjà à l'échelle)
        self.document = QTextDocument(self)
        self.document.setDocumentMargin(0)
        self.document.setDefaultFont(police(taille, graisse))
        # Coupe aux espaces si possible, sinon n'importe où.
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.document.setDefaultTextOption(option)
        # Couleur par défaut ; les <span> colorés à l'intérieur la remplacent.
        self.document.setHtml(f'<span style="color:{couleur}">{html_texte}</span>')
        self.document.setTextWidth(largeur - retrait)
        self.setFixedHeight(math.ceil(self.document.size().height()))

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.translate(self.retrait, 0)
        self.document.drawContents(peintre)


class EtiquetteNiveau(QFrame):
    """Le cadre « intermédiaire ■■□□ » en haut à droite."""

    def __init__(self, niveau: int, nom: str, info_bulle: str):
        super().__init__()
        couleur = COULEURS_NIVEAUX[niveau]
        self.setObjectName("niveau")
        self.setStyleSheet(f"#niveau {{ border: {px(TRAIT)}px solid rgba(255, 255, 255, 0.16);"
                           f" background: rgba(0, 0, 0, 0.18); border-radius: {px(4)}px; }}")
        self.setToolTip(info_bulle)
        ligne = QHBoxLayout(self)
        ligne.setContentsMargins(px(7), px(3), px(7), px(3))
        ligne.setSpacing(px(3))
        ligne.addWidget(etiquette(nom, couleur, 11, QFont.Weight.DemiBold))
        ligne.addSpacing(px(4))
        for i in range(1, 5):
            carre = QFrame()
            carre.setFixedSize(px(10), px(10))
            if i <= niveau:
                carre.setStyleSheet(f"background: {couleur}; border: none;"
                                    f" border-radius: {px(1)}px;")
            else:
                carre.setStyleSheet(f"background: transparent; border-radius: {px(1)}px;"
                                    f" border: {px(TRAIT)}px solid rgba(255, 255, 255, 0.35);")
            ligne.addWidget(carre)


class BlocPaire(QFrame):
    """Commande + commande inverse, reliées par un trait jaune vertical à gauche."""

    def __init__(self):
        super().__init__()
        self.setObjectName("paire")
        self.setStyleSheet(f"#paire {{ border: none;"
                           f" border-left: {px(TRAIT_PAIRE_LARGE)}px solid {TRAIT_PAIRE}; }}")
        self.colonne = QVBoxLayout(self)
        self.colonne.setContentsMargins(px(MARGE_PAIRE), 0, 0, 0)
        self.colonne.setSpacing(px(ESPACE))


class Fenetre(QWidget):
    """La fenêtre principale."""

    def __init__(self, serie: list[dict], niveau: int, date: datetime.date,
                 langue: str, disponibles: list[str], au_changement_de_langue=None):
        super().__init__()
        self.serie = serie
        self.niveau = niveau
        self.date = date
        self.langue = langue
        self.disponibles = disponibles
        self.au_changement_de_langue = au_changement_de_langue

        self.setWindowTitle("TuxDay")
        # Pas de bordure système ; fond transparent (on dessine le nôtre).
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(px(LARGEUR))

        # La fenêtre contient un seul widget, `contenu`, refait à chaque changement de langue.
        self.cadre = QVBoxLayout(self)
        self.cadre.setContentsMargins(0, 0, 0, 0)
        self.contenu = None
        self.construire()

    # --- Dessin du fond --------------------------------------------------------

    def paintEvent(self, event):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        epaisseur = px(TRAIT)
        peintre.setPen(QPen(BORDURE, epaisseur))
        peintre.setBrush(FOND)
        # Le trait est centré sur le bord : on rentre d'une demi-épaisseur
        # pour qu'il tombe pile sur les pixels.
        d = epaisseur / 2
        peintre.drawRoundedRect(self.rect().toRectF().adjusted(d, d, -d, -d),
                                px(RAYON), px(RAYON))

    # --- Construction du contenu ---------------------------------------------

    def construire(self):
        """Crée tout le contenu de la fenêtre dans la langue courante."""
        t = langues.charger_langue(self.langue)
        self.textes = t

        # Un nouveau conteneur remplace l'ancien (s'il y en avait un).
        if self.contenu is not None:
            self.cadre.removeWidget(self.contenu)
            self.contenu.hide()
            self.contenu.deleteLater()   # supprimé pour de bon un instant plus tard
        self.contenu = QWidget()
        self.colonne = QVBoxLayout(self.contenu)
        self.colonne.setContentsMargins(px(MARGE_COTES), px(10), px(MARGE_COTES), px(12))
        self.colonne.setSpacing(px(ESPACE))

        self.colonne.addLayout(self.en_tete(t))
        self.colonne.addWidget(TexteRiche(html.escape(t["intro"]), 12, GRIS, largeur_contenu()))

        for numero, entree in enumerate(self.serie, start=1):
            self.ajouter_commande(numero, entree, t)

        self.colonne.addSpacing(px(2))
        self.colonne.addWidget(trait_horizontal(TRAIT_PIED))
        self.colonne.addLayout(self.pied(t))

        self.cadre.addWidget(self.contenu)
        self.contenu.show()   # nécessaire si la fenêtre est déjà affichée
        # Hauteur de la fenêtre = hauteur du contenu.
        self.setFixedHeight(self.colonne.sizeHint().height())

    def en_tete(self, t: dict) -> QHBoxLayout:
        ligne = QHBoxLayout()
        ligne.setSpacing(px(8))
        ligne.addWidget(etiquette(t["title"], CYAN, 14, QFont.Weight.Bold))
        ligne.addStretch()
        ligne.addWidget(EtiquetteNiveau(self.niveau, t["levels"][str(self.niveau)],
                                        t["level_tooltip"].format(n=self.niveau)))
        fermer = QPushButton("✕")
        fermer.setFont(police(13))
        fermer.setToolTip(t["close_tooltip"])
        fermer.setCursor(Qt.CursorShape.PointingHandCursor)
        fermer.setFlat(True)
        fermer.setStyleSheet(f"QPushButton {{ color: {GRIS}; border: none; padding: 0 {px(2)}px; }}"
                             "QPushButton:hover { color: #ffffff; }")
        fermer.clicked.connect(self.close)
        ligne.addWidget(fermer)
        return ligne

    def titre_section(self, numero: int, entree: dict, t: dict) -> QHBoxLayout:
        """« 1 · SHELL  navigation ───────── »"""
        ligne = QHBoxLayout()
        ligne.setSpacing(px(8))
        ligne.addWidget(etiquette(f"{numero} · {entree['type'].upper()}", CYAN, 11,
                                  QFont.Weight.Bold))
        if "inverse" in entree:
            theme = t["pair_label"]
        else:
            theme = t["themes"].get(entree["theme"], entree["theme"])
        ligne.addWidget(etiquette(theme, GRIS, 11))
        ligne.addWidget(trait_horizontal(TRAIT_SECTION), 1, Qt.AlignmentFlag.AlignVCenter)
        return ligne

    def ligne_commande(self, cmd: str, largeur: int, inverse: bool = False) -> TexteRiche:
        invite = ORANGE if inverse else VERT
        texte = f'<span style="color:{invite}">$</span> ' + coloration.html_commande(cmd)
        if inverse:
            texte += (f' <span style="color:{ORANGE}; font-size:{px(11)}px; font-weight:400">'
                     f'&nbsp;{self.textes["inverse"]}</span>')
        return TexteRiche(texte, 13, coloration.BLANC, largeur, QFont.Weight.DemiBold)

    def ligne_explication(self, explication: str, cmd: str, largeur: int) -> TexteRiche:
        # Décalée vers la droite (14 px à l'échelle 1).
        return TexteRiche(coloration.html_explication(explication, cmd), 12, LAVANDE,
                          largeur, retrait=px(RETRAIT))

    def ajouter_commande(self, numero: int, entree: dict, t: dict):
        self.colonne.addLayout(self.titre_section(numero, entree, t))
        expl = langues.explication(entree["explain"], self.langue)

        if "inverse" not in entree:
            self.colonne.addWidget(self.ligne_commande(entree["cmd"], largeur_contenu()))
            self.colonne.addWidget(self.ligne_explication(expl, entree["cmd"], largeur_contenu()))
            return

        inv = entree["inverse"]
        paire = BlocPaire()
        paire.colonne.addWidget(self.ligne_commande(entree["cmd"], largeur_paire()))
        paire.colonne.addWidget(self.ligne_explication(expl, entree["cmd"], largeur_paire()))
        paire.colonne.addWidget(self.ligne_commande(inv["cmd"], largeur_paire(), inverse=True))
        paire.colonne.addWidget(self.ligne_explication(
            langues.explication(inv["explain"], self.langue), inv["cmd"], largeur_paire()))
        self.colonne.addWidget(paire)

    def pied(self, t: dict) -> QHBoxLayout:
        ligne = QHBoxLayout()
        ligne.setSpacing(px(4))
        for i, code in enumerate(self.disponibles):
            if i:
                ligne.addWidget(etiquette("|", GRIS_INACTIF, 11))
            ligne.addWidget(self.bouton_langue(code, t))
        ligne.addSpacing(px(10))
        serie = t["series"].format(date=self.date.strftime(t["date_format"]))
        ligne.addWidget(etiquette(serie, GRIS, 11))
        ligne.addStretch()

        fini = QPushButton(t["done"])
        fini.setFont(police(12))
        fini.setCursor(Qt.CursorShape.PointingHandCursor)
        fini.setStyleSheet(f"QPushButton {{ color: {VERT};"
                           f" border: {px(TRAIT)}px solid rgba(143, 227, 168, 0.6);"
                           " background: rgba(143, 227, 168, 0.12);"
                           f" border-radius: {px(4)}px; padding: {px(3)}px {px(10)}px; }}"
                           "QPushButton:hover { background: rgba(143, 227, 168, 0.25); }")
        fini.clicked.connect(self.close)
        ligne.addWidget(fini)
        return ligne

    def bouton_langue(self, code: str, t: dict) -> QPushButton:
        bouton = QPushButton(code)
        bouton.setToolTip(t["language_tooltip"])
        bouton.setCursor(Qt.CursorShape.PointingHandCursor)
        if code == self.langue:
            bouton.setFont(police(11, QFont.Weight.Bold))
            bouton.setStyleSheet(f"QPushButton {{ color: {CYAN};"
                                 " background: rgba(127, 211, 245, 0.20);"
                                 f" border: none; border-radius: {px(3)}px;"
                                 f" padding: {px(1)}px {px(5)}px; }}")
        else:
            bouton.setFont(police(11))
            bouton.setStyleSheet(f"QPushButton {{ color: {GRIS_INACTIF}; background: transparent;"
                                 f" border: none; border-radius: {px(3)}px;"
                                 f" padding: {px(1)}px {px(5)}px; }}"
                                 "QPushButton:hover { color: #ffffff; }")
        bouton.clicked.connect(lambda: self.changer_langue(code))
        return bouton

    def changer_langue(self, code: str):
        if code == self.langue:
            return
        self.langue = code
        if self.au_changement_de_langue:
            self.au_changement_de_langue(code)   # enregistre dans config.json
        self.construire()
