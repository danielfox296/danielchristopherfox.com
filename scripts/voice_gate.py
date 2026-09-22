#!/usr/bin/env python3
"""Voice gate for danielchristopherfox.com (2026-09-19).

Encodes the greppable half of ../00-START-HERE.md (Hard rules: no em dashes in
body, no "it's not X, it's Y", never "psychologist", the cut figures, no
therapy or treatment claims) and the estate catalog at
~/Desktop/site-ops/AI-TELLS-2026.md (BASE-VOICE rule 9).

HITS fail the gate (exit 1): em dashes (typed or &mdash;), "quietly", the cut
figures (750% and 1,500%), Daniel described as a psychologist, the 2023-26
tell lexicon, sincerity markers, candor flags, and body copy that links the
site's own home page (the old video-outro self-plug).

NOTES print for the read and never fail: the greppable shapes of a definition
by negation, "the chair" (the retired producer's-chair image), "plainly",
therapy and treatment diction outside the sanctioned clinician lines, other
uses of "psychologist" (fine when it names a researcher), uncontracted forms
on the marketing surfaces (notes, spokes, pillar), paragraphs closing on a
fragment, and any section whose register-cluster density (seat, carry, land,
hold, earn, legible, proof, the read, the story, the number) reaches three
distinct words. The essays keep their formal cadence on purpose, so the
uncontracted note does not run on essay-* pages.

Scans _src/pages/**/sections/*.html (HTML comments and scripts stripped),
every config.json's title, meta_description, schema headline/description and
faq, the partials, and the built llms.txt when it exists.
Run: python3 scripts/voice_gate.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "_src"

SANCTIONED = (
    "It isn't a treatment and I'm not a clinician",
    "I cannot treat them, and I will not pretend the soundtrack is the care",
)

HITS = [
    ("em dash", re.compile("—|&mdash;"), "no em dashes anywhere on the estate (START-HERE, BASE-VOICE)"),
    ("quietly", re.compile(r"\bquietly\b", re.I), "the word never publishes"),
    ("cut figure", re.compile(r"\b750\s?%|\b750 percent|\b1,?500\s?%|\b1,?500 percent", re.I), "the 750% and 1,500% figures are cut (START-HERE)"),
    ("psychologist (Daniel)", re.compile(r"Daniel[^.]{0,60}\bpsychologist\b|\bpsychologist\b[^.]{0,40}\bDaniel\b|\b(music|retail|behavioral) psychologist\b|\bI'?m a psychologist\b|\bI am a psychologist\b", re.I), "never 'psychologist' for Daniel (START-HERE)"),
    ("tell lexicon", re.compile(
        r"\b(delve|tapestry|testament|realm|seamless|holistic|multifaceted|leverage|synergy|robust|"
        r"elevate|unlock|unlocks|unlocked|supercharge|load-bearing|full stop|belt and suspenders|smoking gun|"
        r"the unlock|does the heavy lifting|chef's kiss|at its core|it's worth noting|worth noting|"
        r"worth stating plainly|put differently|the version of|the version where|"
        r"the shape of|the trap|the move\b|the work is the work|navigate|journey)\b", re.I),
     "AI-TELLS Layer 1 and 2"),
    ("sincerity marker", re.compile(r"\b(genuinely|truly)\b|\bI mean that\b|\bI'm upfront\b", re.I), "prose that vouches for itself"),
    ("candor flag", re.compile(r"\bhonest(ly)?\b|\bcandidly\b|\bfull disclosure\b|straight answer|tell you straight|be straight with", re.I),
     "state the thing without a label"),
    ("self-link", re.compile(r'href="https://danielchristopherfox\.com/?"'), "body copy linking the site's own home page (the old video outro); link The Work instead"),
]
NOTES = [
    ("negation shape", re.compile(r", not (a |an |the |just )?[a-z]|\b(isn't|is not|aren't|wasn't) (a |an |the )?[^.]{1,50}\. (It's|It is|They're|That's)\b", re.I)),
    ("the chair", re.compile(r"\bthe chair\b", re.I)),
    ("plainly", re.compile(r"\bplainly\b", re.I)),
    ("psychologist", re.compile(r"\bpsychologist\b", re.I)),
    ("therapy diction", re.compile(r"\b(therapy|therapeutic|treatment|treat|cure|cures|clinical)\b", re.I)),
]
UNCONTRACTED = re.compile(r"\b(it|that|there|here) is\b|\b(they|we|you) (are|will)\b|\bI (am|will|have|would)\b|\b(do|does|did|is|are|was|were|can|could|would|should|will|have|has|had) not\b|\bcannot\b")
CLUSTER = re.compile(r"\b(seat|carry|carries|carried|carrying|land|lands|landed|landing|hold|holds|held|holding|earn|earns|earned|legible|proof|the read|the story|the number)\b", re.I)
SHORT_CLOSER = re.compile(r"(?:^|\.\s+)([A-Z][^.!?]{0,20}[.!?])\s*$")


def strip_markup(text):
    text = re.sub(r"<[^>]+>", " ", text)
    return (text.replace("&rsquo;", "'").replace("&#x27;", "'").replace("&amp;", "&")
                .replace("&middot;", "·").replace("&rarr;", "→").replace("&larr;", "←"))


def texts():
    for p in sorted(SRC.glob("pages/**/sections/*.html")):
        raw = p.read_text()
        raw = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)
        raw = re.sub(r"<script.*?</script>", "", raw, flags=re.DOTALL)
        yield p, raw, True
    for p in sorted(SRC.glob("pages/**/config.json")):
        cfg = json.loads(p.read_text())
        parts = [str(cfg.get("title", "")), str(cfg.get("meta_description", ""))]
        sch = cfg.get("schema")
        if isinstance(sch, dict):
            parts += [str(sch.get("headline", "")), str(sch.get("description", ""))]
        elif isinstance(sch, str):
            parts.append(sch)
        for qa in cfg.get("faq", []) or []:
            parts += [qa.get("q", ""), qa.get("a", "")]
        yield p, "\n".join(parts), False
    for p in (SRC / "partials" / "header.html", SRC / "partials" / "footer.html", SRC / "partials" / "head.html", ROOT / "llms.txt"):
        if p.exists():
            yield p, p.read_text(), False


def main():
    hits, notes = [], []
    for path, raw, is_section in texts():
        rel = path.relative_to(ROOT)
        text = strip_markup(raw)
        for s in SANCTIONED:
            text = text.replace(s, "")
        slug = path.parent.parent.name if is_section else path.parent.name
        for i, line in enumerate(text.splitlines(), 1):
            for label, pat, fix in HITS:
                if pat.search(line):
                    hits.append((rel, i, label, fix, line.strip()[:110]))
            for label, pat in NOTES:
                if pat.search(line):
                    notes.append((rel, i, label, line.strip()[:110]))
        if is_section and slug.split("-")[0] in ("note", "spoke", "pillar"):
            n = len(UNCONTRACTED.findall(text))
            if n >= 3:
                notes.append((rel, 0, "uncontracted density", f"{n} uncontracted forms on a marketing surface"))
        for para in re.split(r"\n\s*\n", text):
            para = " ".join(para.split())
            m = SHORT_CLOSER.search(para)
            if m and len(m.group(1).split()) <= 3 and len(para) > 120:
                notes.append((rel, 0, "short closer", m.group(1)))
        if is_section:
            words = {w.lower() for w in CLUSTER.findall(text)}
            if len(words) >= 3:
                notes.append((rel, 0, "register cluster density", ", ".join(sorted(words))))
    if notes:
        print("Notes (a read, never a failure):")
        for rel, i, label, line in notes:
            print(f"  {rel}{':' + str(i) if i else ''}  {label}: {line}")
    if hits:
        print("\nHITS:")
        for rel, i, label, fix, line in hits:
            print(f"  {rel}:{i}  [{label}] {line}\n      -> {fix}")
        print(f"\n{len(hits)} hit(s).")
        return 1
    print("\nGate clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
