"""Tests voor de validator.

Draaien vanuit de hoofdmap van de repository:
    python -m unittest discover tools/tests
"""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

# Zorg dat Python validate_fish.py in de map tools/ kan vinden.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scheldwoorden import contains_bad_word, word_hash
from validate_fish import (
    check_unique_names,
    load_options,
    validate_blocked_words,
    validate_file_name,
    validate_files,
    validate_fish,
)

GOOD_FISH = {
    "name": "Testvis",
    "maker": "Tester",
    "body": "round",
    "fins": "small",
    "pattern": "none",
    "colors": {"body": "#ff8800", "fins": "#ffffff", "pattern": "#222222"},
    "size": 1.0,
    "speed": 1.0,
    "behavior": "calm",
}


class ValidateFishTest(unittest.TestCase):
    def setUp(self):
        self.options = load_options()
        # Elke test krijgt een eigen kopie, zodat tests elkaar niet beïnvloeden.
        self.fish = copy.deepcopy(GOOD_FISH)

    def test_good_fish_has_no_errors(self):
        self.assertEqual(validate_fish(self.fish, self.options, "testvis.json"), [])

    def test_missing_field(self):
        del self.fish["maker"]
        errors = validate_fish(self.fish, self.options, "testvis.json")
        self.assertEqual(len(errors), 1)
        self.assertIn("'maker' ontbreekt", errors[0])

    def test_unknown_option(self):
        self.fish["fins"] = "puntig"
        errors = validate_fish(self.fish, self.options, "testvis.json")
        self.assertEqual(len(errors), 1)
        self.assertIn("'fins' is 'puntig'", errors[0])

    def test_wrong_color(self):
        self.fish["colors"]["body"] = "oranje"
        errors = validate_fish(self.fish, self.options, "testvis.json")
        self.assertEqual(len(errors), 1)
        self.assertIn("colors.body", errors[0])

    # De scheldwoordcontrole testen we met verzonnen woorden, zodat er geen echte in de repo staan.
    TEST_WORDS = ({word_hash("stoutwoord"), word_hash("heel stout")}, {word_hash("foei")})

    def test_bad_word_whole(self):
        self.assertTrue(contains_bad_word("Mijn Stoutwoord", self.TEST_WORDS))

    def test_bad_word_phrase(self):
        self.assertTrue(contains_bad_word("Heel... stout!", self.TEST_WORDS))

    def test_bad_word_whole_only_as_whole_word(self):
        self.assertFalse(contains_bad_word("Stoutwoordenboek", self.TEST_WORDS))

    def test_bad_word_anywhere(self):
        self.assertTrue(contains_bad_word("Foeivis", self.TEST_WORDS))

    def test_bad_word_tricks(self):
        self.assertTrue(contains_bad_word("F.0.é.1", self.TEST_WORDS))
        self.assertTrue(contains_bad_word("S t o u t w o o r d", self.TEST_WORDS))

    def test_bad_word_error_message(self):
        self.fish["maker"] = "Foei"
        errors = validate_blocked_words(self.fish, self.TEST_WORDS, "testvis.json")
        self.assertEqual(len(errors), 1)
        self.assertIn("'maker'", errors[0])

    def test_normal_names_pass_real_list(self):
        for name in ["Hoera", "Kutlu", "Nazir", "Spike", "Glassy", "Anita", "Schatje", "Silvis"]:
            self.fish["name"] = name
            self.assertEqual(validate_fish(self.fish, self.options, "testvis.json"), [], name)

    def test_duplicate_name(self):
        other = copy.deepcopy(GOOD_FISH)
        other["name"] = "TESTVIS"
        errors = check_unique_names({"fish/a.json": self.fish, "fish/b.json": other})
        self.assertEqual(list(errors), ["fish/b.json"])
        # De melding noemt beide bestanden, zodat de student zijn eigen bestand herkent.
        self.assertIn("fish/a.json", errors["fish/b.json"])
        self.assertIn("fish/b.json", errors["fish/b.json"])

    def test_bad_file_name(self):
        self.assertNotEqual(validate_file_name("fish/Mijn Vis.json"), [])
        self.assertEqual(validate_file_name("fish/mijn-vis.json"), [])



class ValidateFilesTest(unittest.TestCase):
    """Tests met echte bestanden in een tijdelijke map."""

    def setUp(self):
        self.options = load_options()
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

    def write(self, name, text, encoding="utf-8"):
        path = Path(self.folder.name) / name
        path.write_text(text, encoding=encoding)
        return path

    def test_file_with_bom_is_valid(self):
        # Kladblok slaat soms op als "UTF-8 met BOM".
        path = self.write("testvis.json", json.dumps(GOOD_FISH), encoding="utf-8-sig")
        valid_fish, errors = validate_files([path], self.options)
        self.assertEqual(errors, [])
        self.assertIn("testvis", valid_fish)

    def test_file_not_ending_in_json(self):
        path = self.write("testvis.json.txt", json.dumps(GOOD_FISH))
        valid_fish, errors = validate_files([path], self.options)
        self.assertEqual(len(errors), 1)
        self.assertIn("eindigt niet op .json", errors[0])
        self.assertEqual(valid_fish, {})


if __name__ == "__main__":
    unittest.main()
