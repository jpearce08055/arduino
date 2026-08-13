#!/usr/bin/env python3
"""Check that CW_Practice_Keyer.ino contains the standard ITU Morse table."""

from pathlib import Path
import re
import sys

ITU = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "0": "-----",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    ".": ".-.-.-",
    ",": "--..--",
    "?": "..--..",
    "/": "-..-.",
    "=": "-...-",
}

SKETCH = Path(__file__).resolve().parents[1] / "CW_Practice_Keyer" / "CW_Practice_Keyer.ino"
source = SKETCH.read_text(encoding="utf-8")
pattern = re.compile(r"case '([^']+)': return \"([.-]+)\";")
found = dict(pattern.findall(source))

errors = []
for symbol, code in ITU.items():
    if symbol not in found:
        errors.append(f"missing {symbol}")
    elif found[symbol] != code:
        errors.append(f"{symbol}: expected {code}, found {found[symbol]}")

if errors:
    print("Morse table check failed:")
    for error in errors:
        print(f"  {error}")
    sys.exit(1)

print(f"OK: {len(ITU)} ITU Morse symbols match {SKETCH.name}")
