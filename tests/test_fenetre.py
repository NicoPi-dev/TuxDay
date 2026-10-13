"""Tests de l'échelle de tuxday/fenetre.py (sans ouvrir de fenêtre)."""

import unittest

from tuxday import fenetre


class TestEchelle(unittest.TestCase):

    def tearDown(self):
        fenetre.definir_echelle(1.3)

    def test_px(self):
        fenetre.definir_echelle(1.0)
        self.assertEqual(fenetre.px(540), 540)
        fenetre.definir_echelle(1.3)
        self.assertEqual(fenetre.px(540), 702)
        self.assertEqual(fenetre.px(10), 13)
        self.assertEqual(fenetre.px(0), 0)

    def test_un_trait_reste_visible(self):
        fenetre.definir_echelle(0.5)
        self.assertEqual(fenetre.px(1), 1)

    def test_largeurs(self):
        fenetre.definir_echelle(1.0)
        self.assertEqual(fenetre.largeur_contenu(), 512)
        self.assertEqual(fenetre.largeur_paire(), 500)


if __name__ == "__main__":
    unittest.main()
