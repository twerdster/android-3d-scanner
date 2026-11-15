#!/usr/bin/env python3
"""Check the selected numerical method bodies against the historical source offline."""
import hashlib
from pathlib import Path
import re

root = Path(__file__).resolve().parent
original = root.parents[1] / "source/src/com/project/logic/Reconstructor.java"
source = original.read_text()
adaptation = (root / "app/src/main/java/org/technion/beamreplay/HistoricalNumerics.java").read_text()
expected = "720351709b2c5f6219cf2779ff5bef7c09380d934d601b1625b966e9e972ad4b"
assert hashlib.sha256(original.read_bytes()).hexdigest() == expected


def method(text, name):
    start = text.index("private void")
    opening = text.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return re.sub(r"\s+", "", text[start:end])


for name in ["DecodeGraySimpleBW", "NormalizeDecodedValues", "CorrectOpticalDistortionCPU", "ReconstructCPU"]:
    # Original contains call sites before definitions; search definitions explicitly.
    definition = re.search(r"private void\s+" + name + r"\(", source).start()
    selected = re.search(r"private void\s+" + name + r"\(", adaptation).start()
    assert method(source[definition:], name) == method(adaptation[selected:], name), name
print("PASS: source hash and all four numerical method bodies match (whitespace ignored).")
