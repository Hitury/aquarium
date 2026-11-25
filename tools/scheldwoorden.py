"""Scheldwoorden herkennen zonder dat de woorden zelf in de repository staan.

In shared/scheldwoorden.json staan alleen hashes (SHA-256, de eerste 16 tekens) van de
woorden. Je kunt een naam dus wel controleren, maar de lijst is niet te lezen.
Let op: dit verbergt de woorden, het is geen echte beveiliging. Wie een woordenlijst
heeft, kan uitzoeken welke woorden erin staan.

Gebruik:
    python tools/scheldwoorden.py test "Naam van een vis"   # mag deze naam?
    python tools/scheldwoorden.py voeg-toe woord            # heel woord toevoegen
    python tools/scheldwoorden.py voeg-toe woord --overal   # ook midden in een naam
    python tools/scheldwoorden.py bouw <map>                # opnieuw bouwen uit leesbare lijsten

Voor 'bouw' staan in <map> (buiten de repository):
    nl.txt, en.txt   hele woorden of woordgroepen (bijvoorbeeld uit de LDNOOBW-lijst, CC BY 4.0)
    eigen.txt        woorden die ook midden in een naam worden afgekeurd
    toegestaan.txt   woorden uit nl.txt/en.txt die wel mogen
Eén woord per regel; regels die met # beginnen zijn uitleg.

De Vissenmaker (maker/maker.js) doet precies dezelfde controle in de browser.
"""

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORDS_FILE = ROOT / "shared" / "scheldwoorden.json"
# Langer dan dit aantal woorden achter elkaar wordt niet als woordgroep gecontroleerd.
MAX_PHRASE = 6
# Korter dan dit aantal letters wordt niet midden in een naam gezocht.
MIN_PART = 3


def simplify(text):
    """Kleine letters, zonder accenten; cijfers die op letters lijken worden letters;
    al het andere wordt een spatie. "B.ú.0" wordt "b u o"."""
    text = unicodedata.normalize("NFD", text.strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.translate(str.maketrans("013457@$", "oieastas"))
    return " ".join(re.sub(r"[^a-z]", " ", text).split())


def word_hash(text):
    """De eerste 16 tekens van de SHA-256-hash van een (vereenvoudigd) woord."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load(path=WORDS_FILE):
    """Leest shared/scheldwoorden.json. Geeft (hele_woorden, overal) als sets met hashes."""
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return set(), set()
    return set(data.get("heel", [])), set(data.get("overal", []))


def contains_bad_word(text, words):
    """True als de tekst een scheldwoord bevat.

    - hele woorden en woordgroepen uit 'heel' ("Glassy" bevat dus niet "ass")
    - de hele naam aan elkaar geschreven ("f o e i" telt als "foei")
    - elk stuk van minstens MIN_PART letters uit 'overal' (ook midden in "Foeivis")
    """
    whole, anywhere = words
    parts = simplify(text).split()
    for start in range(len(parts)):
        for end in range(start + 1, min(start + MAX_PHRASE, len(parts)) + 1):
            if word_hash(" ".join(parts[start:end])) in whole:
                return True
    glued = "".join(parts)
    if glued and word_hash(glued) in whole:
        return True
    for start in range(len(glued)):
        for end in range(start + MIN_PART, len(glued) + 1):
            if word_hash(glued[start:end]) in anywhere:
                return True
    return False


def read_list(path):
    """Leest een leesbare woordenlijst en vereenvoudigt elk woord."""
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as file:
        words = [simplify(line) for line in file if not line.strip().startswith("#")]
    return [word for word in words if word]


def save(whole, anywhere, path=WORDS_FILE):
    content = {
        "uitleg": "Hashes van scheldwoorden, zie tools/scheldwoorden.py. "
                  "Bron van een deel van de woorden: List of Dirty, Naughty, Obscene, and Otherwise Bad Words "
                  "(github.com/LDNOOBW), licentie CC BY 4.0.",
        "heel": sorted(whole),
        "overal": sorted(anywhere),
    }
    with open(path, "w", encoding="utf-8") as file:
        json.dump(content, file, indent=1)
        file.write("\n")


def build(folder):
    folder = Path(folder)
    allowed = set(read_list(folder / "toegestaan.txt"))
    whole = (set(read_list(folder / "nl.txt")) | set(read_list(folder / "en.txt"))) - allowed
    anywhere = set(read_list(folder / "eigen.txt"))
    save({word_hash(word) for word in whole}, {word_hash(word) for word in anywhere})
    print(f"{WORDS_FILE.relative_to(ROOT).as_posix()} geschreven: {len(whole)} hele woorden, {len(anywhere)} overal.")


def main(arguments):
    if len(arguments) >= 2 and arguments[0] == "test":
        name = " ".join(arguments[1:])
        if contains_bad_word(name, load()):
            print(f"'{name}' wordt afgekeurd.")
            return 1
        print(f"'{name}' mag.")
        return 0
    if len(arguments) >= 2 and arguments[0] == "voeg-toe":
        word = simplify(arguments[1])
        whole, anywhere = load()
        (anywhere if "--overal" in arguments else whole).add(word_hash(word))
        save(whole, anywhere)
        print("Toegevoegd.")
        return 0
    if len(arguments) == 2 and arguments[0] == "bouw":
        build(arguments[1])
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
