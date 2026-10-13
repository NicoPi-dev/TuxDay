"""Tests de tuxday/coloration.py. Lancer : python3 -m unittest -v"""

import unittest

from tuxday.coloration import (BLANC, CYAN, JAUNE, couleurs_commande, html_commande,
                               html_explication, noms_de_commandes)


def mots_colores(cmd):
    """Liste (mot, couleur) sans les espaces, pour des tests lisibles."""
    return [(t, c) for t, c in couleurs_commande(cmd) if not t.isspace()]


class TestColoration(unittest.TestCase):

    def test_commande_simple(self):
        self.assertEqual(mots_colores("df -h /home"),
                         [("df", JAUNE), ("-h", CYAN), ("/home", BLANC)])

    def test_apres_pipe_et_separateurs(self):
        self.assertEqual(noms_de_commandes("ls -l | sort -r && echo ok ; pwd || true"),
                         {"ls", "sort", "echo", "pwd", "true"})

    def test_pipe_entre_guillemets(self):
        self.assertEqual(noms_de_commandes('grep -E "a|b" fichier | wc -l'), {"grep", "wc"})
        self.assertIn(('"a|b"', BLANC), mots_colores('grep -E "a|b" fichier'))

    def test_python(self):
        self.assertEqual(mots_colores("python3 -c \"print('-x')\""),
                         [("python3", JAUNE), ("-c", CYAN), ("\"print('-x')\"", BLANC)])
        self.assertEqual(mots_colores("python3 -m json.tool"),
                         [("python3", JAUNE), ("-m", CYAN), ("json.tool", BLANC)])

    def test_html_echappe(self):
        self.assertIn("&lt;", html_commande("echo a < b"))
        self.assertNotIn("<b", html_commande("echo <b>"))

    def test_explication(self):
        cmd = "mkdir -p ~/essai_linux/a"
        html = html_explication("`mkdir` crée ; `-p` crée les parents ; `a` est la cible.", cmd)
        self.assertNotIn("`", html)
        self.assertIn(f'color:{JAUNE}">mkdir<', html)
        self.assertIn(f'color:{CYAN}">-p<', html)
        self.assertIn(f'color:{BLANC}">a<', html)

    def test_mot_cle_en_plusieurs_mots(self):
        html = html_explication("`python3 -c` exécute le code.", 'python3 -c "print(1)"')
        self.assertIn(f'color:{JAUNE}">python3<', html)
        self.assertIn(f'color:{CYAN}">-c<', html)

    def test_toute_la_bibliotheque(self):
        # Aucune commande ne doit faire planter la coloration.
        from tuxday import tirage
        for e in tirage.charger_commandes():
            for cmd in [e["cmd"]] + ([e["inverse"]["cmd"]] if "inverse" in e else []):
                self.assertEqual("".join(t for t, _ in couleurs_commande(cmd)), cmd)
                html_explication(e["explain"]["fr"], cmd)


if __name__ == "__main__":
    unittest.main()
