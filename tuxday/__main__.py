"""Point d'entrée : `python3 -m tuxday`.

Options utiles pour tester :
  --niveau N          force le niveau du jour (1 à 4)
  --date AAAA-MM-JJ   simule une autre date
  --reset             efface l'état (commandes vues, niveau de la veille)
  --lang xx           force la langue
"""

import argparse
import datetime
import sys

from tuxday import DOSSIER_ASSETS, etat, langues, tirage


def lire_arguments(argv=None) -> argparse.Namespace:
    """Décrit et lit les options de la ligne de commande."""
    parseur = argparse.ArgumentParser(prog="tuxday",
                                      description="4 commandes par jour pour apprendre Linux.")
    parseur.add_argument("--niveau", type=int, choices=[1, 2, 3, 4],
                         help="force le niveau du jour")
    parseur.add_argument("--date", type=datetime.date.fromisoformat,
                         help="simule une autre date (AAAA-MM-JJ)")
    parseur.add_argument("--reset", action="store_true",
                         help="efface l'état (commandes vues, niveau de la veille)")
    parseur.add_argument("--lang", help="force la langue (ex. fr, en)")
    return parseur.parse_args(argv)


def icone_tuxday():
    """Le logo de TuxDay, pris dans assets/ : version simplifiée pour les petites tailles."""
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QIcon

    icone = QIcon()
    for taille in (16, 22, 24, 32):
        icone.addFile(str(DOSSIER_ASSETS / "tuxday-small.svg"), QSize(taille, taille))
    for taille in (48, 64, 128, 256, 512):
        icone.addFile(str(DOSSIER_ASSETS / "tuxday.svg"), QSize(taille, taille))
    return icone


def main(argv=None) -> int:
    args = lire_arguments(argv)

    # Une seule fenêtre TuxDay à la fois : si une autre tourne déjà, on s'arrête
    # avant de toucher à l'état. `verrou` reste ouvert jusqu'à la fin du programme.
    verrou = etat.prendre_verrou()
    if verrou is None:
        print("TuxDay est déjà ouvert.", file=sys.stderr)
        return 0

    # Le dossier où les commandes du jour créent leurs fichiers.
    etat.creer_dossier_essai()

    if args.reset:
        etat.effacer_etat()

    # Langue : --lang, sinon config.json, sinon langue du système.
    config = etat.charger_config()
    disponibles = langues.langues_disponibles()
    code = langues.choisir_langue(args.lang, config.get("langue"), disponibles)

    # Série du jour (relue si elle existe déjà, tirée sinon), puis enregistrement.
    donnees = etat.charger_etat()
    aujourdhui = args.date or datetime.date.today()
    serie = tirage.serie_du_jour(donnees, tirage.charger_commandes(), aujourdhui,
                                 niveau_force=args.niveau)
    etat.enregistrer_etat(donnees)

    # Import ici : les tests et --help n'ont pas besoin de charger Qt.
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication
    from tuxday import fenetre as module_fenetre

    application = QApplication(sys.argv)
    application.setApplicationName("TuxDay")
    # Nom de classe de la fenêtre : c'est grâce à lui que la règle KWin la reconnaît.
    QGuiApplication.setDesktopFileName("tuxday")
    # Icône de la fenêtre (Alt+Tab, aperçus...). Sous Wayland, KDE prend plutôt
    # celle du fichier tuxday.desktop ; celle-ci sert quand il n'est pas installé.
    application.setWindowIcon(icone_tuxday())

    # Échelle de la fenêtre. Si la clé "echelle" manque dans config.json,
    # on l'y écrit avec sa valeur par défaut : l'utilisateur la trouve et peut la changer.
    if "echelle" not in config:
        config["echelle"] = module_fenetre.ECHELLE
        etat.enregistrer_config(config)
    module_fenetre.definir_echelle(etat.lire_echelle(config, module_fenetre.ECHELLE))

    def memoriser_langue(nouvelle: str):
        config["langue"] = nouvelle
        etat.enregistrer_config(config)

    # Boutons de langue : celle du système en premier.
    ordre = langues.ordre_affichage(disponibles)
    fenetre = module_fenetre.Fenetre(serie, donnees["niveau"], aujourdhui, code, ordre,
                                     au_changement_de_langue=memoriser_langue)
    fenetre.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
