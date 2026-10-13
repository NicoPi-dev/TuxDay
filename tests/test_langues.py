"""Tests de tuxday/langues.py. Lancer : python3 -m unittest -v"""

import json
import tempfile
import unittest
from pathlib import Path

from tuxday import langues


class TestLangues(unittest.TestCase):

    def setUp(self):
        # Un dossier de langues temporaire, pour ne pas dépendre des vrais fichiers.
        self._tmp = tempfile.TemporaryDirectory()
        self.dossier = Path(self._tmp.name)
        self._ecrire("fr", {"intro": "Bonjour", "done": "Fini",
                            "themes": {"bases": "bases", "texte": "texte"}})
        self._ecrire("en", {"intro": "Hello", "themes": {"bases": "basics"}})

    def tearDown(self):
        self._tmp.cleanup()

    def _ecrire(self, code, contenu):
        (self.dossier / f"{code}.json").write_text(json.dumps(contenu), encoding="utf-8")

    def test_decouverte_automatique(self):
        self.assertEqual(langues.langues_disponibles(self.dossier), ["en", "fr"])
        self._ecrire("de", {"intro": "Hallo"})
        self.assertEqual(langues.langues_disponibles(self.dossier), ["de", "en", "fr"])

    def test_langue_systeme(self):
        dispo = ["en", "fr"]
        self.assertEqual(langues.langue_systeme(dispo, {"LANG": "fr_FR.UTF-8"}), "fr")
        self.assertEqual(langues.langue_systeme(dispo, {"LANG": "en_US.UTF-8"}), "en")

    def test_langue_systeme_inconnue_donne_anglais(self):
        self.assertEqual(langues.langue_systeme(["en", "fr"], {"LANG": "de_DE.UTF-8"}), "en")
        self.assertEqual(langues.langue_systeme(["en", "fr"], {}), "en")
        self.assertEqual(langues.langue_systeme(["en", "fr"], {"LANG": "C"}), "en")

    def test_priorites_du_choix(self):
        dispo = ["en", "fr"]
        env = {"LANG": "fr_FR.UTF-8"}
        self.assertEqual(langues.choisir_langue("en", "fr", dispo, env), "en")   # --lang
        self.assertEqual(langues.choisir_langue(None, "en", dispo, env), "en")   # config
        self.assertEqual(langues.choisir_langue(None, None, dispo, env), "fr")   # système
        self.assertEqual(langues.choisir_langue("xx", None, dispo, env), "fr")   # inconnue ignorée

    def test_ordre_affichage_langue_systeme_en_premier(self):
        dispo = ["de", "en", "fr"]
        self.assertEqual(langues.ordre_affichage(dispo, {"LANG": "fr_FR.UTF-8"}), ["fr", "de", "en"])
        self.assertEqual(langues.ordre_affichage(dispo, {"LANG": "de_DE.UTF-8"}), ["de", "en", "fr"])
        # Langue du système sans fichier : l'anglais passe en premier.
        self.assertEqual(langues.ordre_affichage(dispo, {"LANG": "it_IT.UTF-8"}), ["en", "de", "fr"])

    def test_libelles_manquants_completes_par_le_francais(self):
        textes = langues.charger_langue("en", self.dossier)
        self.assertEqual(textes["intro"], "Hello")
        self.assertEqual(textes["done"], "Fini")
        self.assertEqual(textes["themes"], {"bases": "basics", "texte": "texte"})

    def test_explication_repli_sur_le_francais(self):
        expl = {"fr": "en français", "en": "in English"}
        self.assertEqual(langues.explication(expl, "en"), "in English")
        self.assertEqual(langues.explication({"fr": "en français"}, "en"), "en français")
        self.assertEqual(langues.explication({"fr": "en français", "de": ""}, "de"), "en français")

    def test_vrais_fichiers_de_langue(self):
        # Les fichiers fournis doivent tous avoir les mêmes clés que le français.
        reference = langues.charger_langue("fr")
        for code in langues.langues_disponibles():
            brut = json.loads((langues.DOSSIER_LANGUES / f"{code}.json").read_text(encoding="utf-8"))
            self.assertEqual(set(brut), set(reference), f"clés différentes dans {code}.json")


if __name__ == "__main__":
    unittest.main()
