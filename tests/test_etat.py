"""Tests de tuxday/etat.py. Lancer : python3 -m unittest -v"""

import tempfile
import unittest
from pathlib import Path

from tuxday import etat


class TestEtat(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dossier = Path(self._tmp.name)
        self.fichier = self.dossier / "tuxday" / "state.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_emplacements_xdg(self):
        env = {"XDG_STATE_HOME": "/tmp/s", "XDG_CONFIG_HOME": "/tmp/c"}
        self.assertEqual(etat.fichier_etat(env), Path("/tmp/s/tuxday/state.json"))
        self.assertEqual(etat.fichier_config(env), Path("/tmp/c/tuxday/config.json"))

    def test_emplacements_par_defaut(self):
        maison = Path.home()
        self.assertEqual(etat.fichier_etat({}), maison / ".local/state/tuxday/state.json")
        self.assertEqual(etat.fichier_config({}), maison / ".config/tuxday/config.json")

    def test_etat_absent(self):
        self.assertEqual(etat.charger_etat(self.fichier), etat.etat_vide())

    def test_etat_abime(self):
        self.fichier.parent.mkdir(parents=True)
        self.fichier.write_text("{pas du json", encoding="utf-8")
        self.assertEqual(etat.charger_etat(self.fichier), etat.etat_vide())

    def test_aller_retour(self):
        donnees = etat.etat_vide()
        donnees.update(date="2026-10-13", niveau=2, serie=["a", "b"], vus=["a", "b"])
        etat.enregistrer_etat(donnees, self.fichier)
        self.assertEqual(etat.charger_etat(self.fichier), donnees)

    def test_reset(self):
        etat.enregistrer_etat({"niveau": 1}, self.fichier)
        etat.effacer_etat(self.fichier)
        self.assertFalse(self.fichier.exists())
        etat.effacer_etat(self.fichier)   # pas d'erreur si déjà absent

    def test_config(self):
        chemin = self.dossier / "config.json"
        self.assertEqual(etat.charger_config(chemin), {})
        etat.enregistrer_config({"langue": "en"}, chemin)
        self.assertEqual(etat.charger_config(chemin), {"langue": "en"})

    def test_echelle(self):
        self.assertEqual(etat.lire_echelle({}, 1.3), 1.3)
        self.assertEqual(etat.lire_echelle({"echelle": 1}, 1.3), 1.0)
        self.assertEqual(etat.lire_echelle({"echelle": 1.5}, 1.3), 1.5)
        for mauvaise in ("grand", None, True, 0, 10, [1]):
            self.assertEqual(etat.lire_echelle({"echelle": mauvaise}, 1.3), 1.3)

    def test_dossier_essai(self):
        cible = self.dossier / "essai_linux"
        etat.creer_dossier_essai(cible)
        etat.creer_dossier_essai(cible)   # une seconde fois : pas d'erreur
        self.assertTrue(cible.is_dir())


    def test_emplacement_verrou(self):
        self.assertEqual(etat.fichier_verrou({"XDG_RUNTIME_DIR": "/run/user/1000"}),
                         Path("/run/user/1000/tuxday.lock"))
        self.assertEqual(etat.fichier_verrou({"XDG_STATE_HOME": "/tmp/s"}),
                         Path("/tmp/s/tuxday/tuxday.lock"))

    def test_verrou_une_seule_instance(self):
        chemin = self.dossier / "tuxday.lock"
        premier = etat.prendre_verrou(chemin)
        self.assertIsNotNone(premier)
        # Tant que le premier tient le verrou, un second lancement est refusé.
        self.assertIsNone(etat.prendre_verrou(chemin))
        # Le premier se ferme : le verrou redevient libre.
        premier.close()
        second = etat.prendre_verrou(chemin)
        self.assertIsNotNone(second)
        second.close()


if __name__ == "__main__":
    unittest.main()
