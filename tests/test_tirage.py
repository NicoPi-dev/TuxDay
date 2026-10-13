"""Tests de tuxday/tirage.py, une classe par règle. Lancer : python3 -m unittest -v"""

import datetime
import random
import unittest

from tuxday import tirage

JOUR = datetime.date(2026, 10, 13)
LENDEMAIN = datetime.date(2026, 10, 14)


def fausse_bibliotheque(par_groupe=6, paires=2):
    """Petite bibliothèque inventée : pour chaque niveau et type, `par_groupe` commandes
    dont les `paires` premières ont une commande inverse."""
    entrees = []
    for niveau in tirage.NIVEAUX:
        for type_ in tirage.TYPES:
            for i in range(par_groupe):
                e = {"id": f"n{niveau}-{type_}-{i}", "level": niveau, "type": type_,
                     "theme": "bases", "cmd": "x", "explain": {"fr": "x"}}
                if i < paires:
                    e["inverse"] = {"cmd": "y", "explain": {"fr": "y"}}
                entrees.append(e)
    return entrees


def tout_present(_exigence):
    """Faux vérificateur : tous les prérequis sont présents."""
    return True


def nouvel_etat():
    return {"date": None, "niveau": None, "niveau_veille": None, "serie": [], "vus": []}


class TestRegle1MemeJour(unittest.TestCase):

    def test_meme_serie_dans_la_journee(self):
        entrees = fausse_bibliotheque()
        etat = nouvel_etat()
        premiere = tirage.serie_du_jour(etat, entrees, JOUR, random.Random(1), tout_present)
        vus_avant = list(etat["vus"])
        # Un autre hasard ne doit rien changer : la série est relue telle quelle.
        seconde = tirage.serie_du_jour(etat, entrees, JOUR, random.Random(99), tout_present)
        self.assertEqual(premiere, seconde)
        self.assertEqual(etat["vus"], vus_avant)

    def test_niveau_force_different_refait_le_tirage(self):
        entrees = fausse_bibliotheque()
        etat = nouvel_etat()
        tirage.serie_du_jour(etat, entrees, JOUR, random.Random(1), tout_present, niveau_force=1)
        serie = tirage.serie_du_jour(etat, entrees, JOUR, random.Random(1), tout_present,
                                     niveau_force=3)
        self.assertTrue(all(e["level"] == 3 for e in serie))
        self.assertIsNone(etat["niveau_veille"])   # même jour : la veille ne bouge pas


class TestRegle2NiveauDuJour(unittest.TestCase):

    def test_jamais_le_niveau_de_la_veille(self):
        rng = random.Random(0)
        for veille in tirage.NIVEAUX:
            tires = {tirage.tirer_niveau(veille, rng) for _ in range(200)}
            # Jamais la veille, et les 3 autres niveaux sont tous possibles.
            self.assertEqual(tires, set(tirage.NIVEAUX) - {veille})

    def test_deux_jours_de_suite(self):
        entrees = fausse_bibliotheque(par_groupe=40)
        etat = nouvel_etat()
        rng = random.Random(5)
        jour = JOUR
        precedent = None
        for _ in range(30):
            tirage.serie_du_jour(etat, entrees, jour, rng, tout_present)
            self.assertNotEqual(etat["niveau"], precedent)
            self.assertEqual(etat["niveau_veille"], precedent)
            precedent = etat["niveau"]
            jour += datetime.timedelta(days=1)


class TestRegle3Composition(unittest.TestCase):

    def test_deux_shell_puis_deux_python_du_bon_niveau(self):
        entrees = fausse_bibliotheque()
        for graine in range(50):
            etat = nouvel_etat()
            serie = tirage.serie_du_jour(etat, entrees, JOUR, random.Random(graine), tout_present)
            self.assertEqual([e["type"] for e in serie], ["shell", "shell", "python", "python"])
            self.assertTrue(all(e["level"] == etat["niveau"] for e in serie))
            self.assertEqual(len({e["id"] for e in serie}), 4)

    def test_au_plus_une_paire_par_bloc(self):
        # Beaucoup de paires : le risque d'en tirer deux est grand si la règle est mal codée.
        entrees = fausse_bibliotheque(par_groupe=6, paires=5)
        for graine in range(200):
            serie = tirage.serie_du_jour(nouvel_etat(), entrees, JOUR, random.Random(graine),
                                         tout_present)
            for bloc in (serie[:2], serie[2:]):
                self.assertLessEqual(sum("inverse" in e for e in bloc), 1)

    def test_jamais_une_commande_deja_vue(self):
        entrees = fausse_bibliotheque()
        etat = nouvel_etat()
        etat["niveau_veille"] = 2
        # Tout est déjà vu au niveau 1, sauf 2 commandes shell et 2 python.
        etat["vus"] = [e["id"] for e in entrees if e["level"] == 1 and not e["id"].endswith(("-4", "-5"))]
        etat["date"] = "2026-10-12"
        etat["niveau"] = 2
        serie = tirage.serie_du_jour(etat, entrees, JOUR, random.Random(3), tout_present,
                                     niveau_force=1)
        self.assertEqual(sorted(e["id"] for e in serie),
                         ["n1-python-4", "n1-python-5", "n1-shell-4", "n1-shell-5"])

    def test_prerequis_absents_exclus(self):
        entrees = fausse_bibliotheque()
        for e in entrees:
            if e["id"].endswith(("-0", "-1", "-2")):
                e["requires"] = ["programme-absent"]
        verifier = lambda exigence: exigence != "programme-absent"
        for graine in range(50):
            serie = tirage.serie_du_jour(nouvel_etat(), entrees, JOUR, random.Random(graine),
                                         verifier)
            self.assertFalse(any("requires" in e for e in serie))

    def test_exigence_satisfaite_sur_la_vraie_machine(self):
        self.assertTrue(tirage.exigence_satisfaite("python3"))
        self.assertFalse(tirage.exigence_satisfaite("programme-qui-n-existe-pas-xyz"))
        self.assertTrue(tirage.exigence_satisfaite("path:~"))
        self.assertTrue(tirage.exigence_satisfaite("path:/us*"))
        self.assertFalse(tirage.exigence_satisfaite("path:/chemin/inexistant*"))
        self.assertTrue(tirage.exigence_satisfaite("py:json"))
        self.assertFalse(tirage.exigence_satisfaite("py:module_inexistant_xyz"))


class TestRegle4Oubli(unittest.TestCase):

    def test_oubli_limite_au_niveau_et_au_type(self):
        entrees = fausse_bibliotheque()
        etat = nouvel_etat()
        tout = [e["id"] for e in entrees]
        etat["vus"] = list(tout)            # tout a déjà été vu
        serie = tirage.serie_du_jour(etat, entrees, JOUR, random.Random(2), tout_present,
                                     niveau_force=2)
        self.assertEqual(len(serie), 4)
        vus = set(etat["vus"])
        for e in entrees:
            if e["level"] == 2:
                # Ce niveau a été oublié : seuls les 4 du jour sont "vus".
                self.assertEqual(e["id"] in vus, e in serie)
            else:
                self.assertIn(e["id"], vus)  # les autres niveaux ne bougent pas

    def test_oubli_d_un_seul_type(self):
        entrees = fausse_bibliotheque()
        etat = nouvel_etat()
        # Niveau 1 : tout le shell vu, rien du python.
        etat["vus"] = [e["id"] for e in entrees if e["level"] == 1 and e["type"] == "shell"]
        tirage.serie_du_jour(etat, entrees, JOUR, random.Random(4), tout_present, niveau_force=1)
        vus = set(etat["vus"])
        self.assertEqual(sum(i.startswith("n1-shell") for i in vus), 2)   # oublié puis 2 tirés
        self.assertEqual(sum(i.startswith("n1-python") for i in vus), 2)  # 2 tirés

    def test_vraiment_impossible(self):
        entrees = [e for e in fausse_bibliotheque(par_groupe=1)]
        with self.assertRaises(tirage.TirageImpossible):
            tirage.serie_du_jour(nouvel_etat(), entrees, JOUR, random.Random(0), tout_present)


class TestRegle5Enregistrement(unittest.TestCase):

    def test_etat_mis_a_jour(self):
        entrees = fausse_bibliotheque()
        etat = nouvel_etat()
        etat["vus"] = ["ancien-id"]
        serie = tirage.serie_du_jour(etat, entrees, JOUR, random.Random(7), tout_present)
        self.assertEqual(etat["date"], "2026-10-13")
        self.assertEqual(etat["serie"], [e["id"] for e in serie])
        self.assertTrue(set(etat["serie"]) <= set(etat["vus"]))
        self.assertIn("ancien-id", etat["vus"])

    def test_nouveau_jour_nouvelle_serie(self):
        entrees = fausse_bibliotheque()
        etat = nouvel_etat()
        hier = tirage.serie_du_jour(etat, entrees, JOUR, random.Random(1), tout_present)
        demain = tirage.serie_du_jour(etat, entrees, LENDEMAIN, random.Random(1), tout_present)
        self.assertTrue({e["id"] for e in hier}.isdisjoint(e["id"] for e in demain))
        self.assertEqual(len(etat["vus"]), 8)


class TestVraieBibliotheque(unittest.TestCase):

    def test_chaque_niveau_peut_fournir_une_serie(self):
        entrees = tirage.charger_commandes()
        for niveau in tirage.NIVEAUX:
            serie = tirage.serie_du_jour(nouvel_etat(), entrees, JOUR, random.Random(niveau),
                                         niveau_force=niveau)
            self.assertEqual(len(serie), 4)


if __name__ == "__main__":
    unittest.main()
