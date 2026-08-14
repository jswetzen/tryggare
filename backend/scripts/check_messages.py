#!/usr/bin/env python
"""Translation-catalogue staleness guard.

Mirrors ``frontend/scripts/check-design-tokens.mjs``: a drift guard that fails
the build instead of letting a surface silently degrade. There, the drift is
between two token files; here it is between the translatable strings actually
present in the source and what the committed ``.po`` catalogues carry.

Django admin is customer-facing (decision D4: tenant administrators are
Django-admin users), and Swedish volunteers read those screens. A missing or
empty catalogue entry does not raise — gettext falls back to the English
msgid — so the failure mode is a screen that quietly goes half-English. That
is exactly the kind of regression a human reviewer will not notice and CI
must.

What counts as stale (and, just as importantly, what does not):

  1. FAIL on a missing msgid. Extraction runs into a temporary directory and
     the extracted msgid *set* is compared against each committed catalogue.
     Any msgid in the source but absent from a catalogue fails.
  2. FAIL on an empty ``msgstr`` in a catalogue that requires translation
     (``sv``). An untranslated entry is the silent degradation above.
  3. FAIL on ``#, fuzzy`` entries. A fuzzy match is gettext telling you it
     guessed; a guess is not a translation.
  4. PASS when ``sv``'s msgstr equals its msgid. "Import", "Status", "Swish"
     and "Bankgiro" are genuinely the same word in both languages. Flagging
     those would be a tempting rule and a wrong one — it would push a
     translator to write something worse purely to satisfy the guard.
  5. NEVER compare file bytes, line counts, or ``#:`` source references.
     Those churn on every unrelated edit, and a guard that fails constantly
     for no reason is a guard people learn to ignore.
  6. FAIL on an invisible character inside a ``msgstr`` (U+200B, U+200C,
     U+FEFF, U+00A0). This is the case that justifies the whole guard: a
     zero-width space sat inside "Incheckn<U+200B>ingstid" — non-empty,
     non-fuzzy, unequal to its msgid, so rules 1-5 all pass it — and it broke
     search and copy-paste on an admin column header while being invisible in
     a diff. Checked on the msgstr ONLY: a msgid is source text, and if a
     developer deliberately writes a non-breaking space into an English
     string, the translator has to be able to mirror it.

Extra msgids in a catalogue that are no longer in the source are reported as
a warning, not a failure: they cost nothing at runtime, and failing on them
would break every branch that deletes a string before the catalogue is
regenerated.

Run:  uv run python scripts/check_messages.py        (from ``backend/``)
      podman exec tryggare_web_1 sh -c \
          'cd /app && uv run python scripts/check_messages.py'

Needs GNU gettext's ``xgettext`` (that is what ``makemessages`` shells out
to). It is present in the backend container image and installed in CI; the
script says so explicitly rather than failing obscurely if it is missing.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
LOCALE_DIR = BACKEND_DIR / "locale"

# Catalogues that must be complete. ``sv`` is the surface volunteers read;
# ``en`` carries every msgid with msgstr == msgid, per the repo convention,
# so that both catalogues are checkable by the same rules.
LANGUAGES = ["en", "sv"]

# Directories makemessages should not walk. ``.venv`` and other dot-dirs are
# skipped by Django itself; these are the ones that are not hidden.
IGNORE = ["staticfiles", "dist", "node_modules", "tests"]

# Rule 6. Characters that render as nothing (or as an ordinary space) but are
# not the character they look like. Each is paired with its Unicode name so
# the failure output can say *which* one, not just "an invisible character".
# Written as escapes on purpose: a literal zero-width space in this source
# file would be exactly as invisible here as it is in a catalogue.
INVISIBLE_CHARS = {
    "\u200b": "U+200B ZERO WIDTH SPACE",
    "\u200c": "U+200C ZERO WIDTH NON-JOINER",
    "\ufeff": "U+FEFF ZERO WIDTH NO-BREAK SPACE (BOM)",
    "\u00a0": "U+00A0 NO-BREAK SPACE",
}


def find_invisible(text: str) -> list[tuple[int, str]]:
    """Return (character offset, Unicode name) for each invisible character.

    The offset is a character index into the msgstr, which is what a person
    needs to find it: the character is invisible, so "somewhere in this
    string" is a puzzle rather than an error message.
    """
    return [
        (index, INVISIBLE_CHARS[char])
        for index, char in enumerate(text)
        if char in INVISIBLE_CHARS
    ]


# --------------------------------------------------------------------------
# .po parsing
#
# Deliberately hand-rolled rather than pulled from ``polib``: the guard must
# run with nothing installed beyond what the backend already depends on, and
# the subset of PO syntax Django emits is small. Only msgid/msgstr and the
# ``#, fuzzy`` flag are needed — locations and translator comments are
# ignored on purpose (rule 5).
# --------------------------------------------------------------------------

# PO escapes only these; everything else in the file is literal UTF-8. Do NOT
# use codecs' "unicode_escape", which would mangle every non-ASCII byte (and
# Swedish is full of them).
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}


def po_unquote(text: str) -> str:
    """Decode one double-quoted PO string literal."""
    match = re.match(r'^\s*"(.*)"\s*$', text)
    if match is None:
        raise ValueError(f"not a quoted PO string: {text!r}")
    body, out, i = match.group(1), [], 0
    while i < len(body):
        char = body[i]
        if char == "\\" and i + 1 < len(body):
            out.append(_ESCAPES.get(body[i + 1], body[i + 1]))
            i += 2
        else:
            out.append(char)
            i += 1
    return "".join(out)


class Entry:
    __slots__ = ("msgid", "msgstr", "fuzzy")

    def __init__(self) -> None:
        self.msgid: str | None = None
        self.msgstr: str = ""
        self.fuzzy: bool = False


def parse_po(path: Path) -> list[Entry]:
    """Parse a .po file into entries. The header (msgid "") is skipped."""
    entries: list[Entry] = []
    current = Entry()
    field: str | None = None

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            if current.msgid is not None:
                entries.append(current)
            current, field = Entry(), None
            continue
        if line.startswith("#"):
            # "#," is the flag line; fuzzy is the only flag this guard reads.
            if line.startswith("#,") and "fuzzy" in line:
                current.fuzzy = True
            continue
        for keyword in ("msgid_plural ", "msgid ", "msgstr "):
            if line.startswith(keyword):
                field = keyword.strip()
                value = po_unquote(line[len(keyword) :])
                if field == "msgid":
                    current.msgid = value
                elif field == "msgstr":
                    current.msgstr = value
                break
        else:
            if line.startswith("msgstr["):
                # Plural form: treat index 0 as the msgstr for emptiness
                # purposes; any empty plural form is still a real gap.
                field = "msgstr"
                current.msgstr += po_unquote(line[line.index("]") + 1 :])
            elif line.startswith('"'):
                if field == "msgid":
                    current.msgid = (current.msgid or "") + po_unquote(line)
                elif field == "msgstr":
                    current.msgstr += po_unquote(line)
                # msgid_plural continuations are ignored.
            else:
                raise ValueError(f"{path}:{lineno}: cannot parse: {raw!r}")

    if current.msgid is not None:
        entries.append(current)
    return [e for e in entries if e.msgid]


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------


def extract_msgids() -> set[str]:
    """Run ``makemessages`` over a throwaway copy of the tree; return msgids.

    The committed catalogues are never touched, and that is load-bearing:
    ``makemessages`` resolves its output directory from ``BASE_DIR`` /
    ``./locale`` relative to where it runs, so pointing it at the real tree
    would rewrite ``locale/*/LC_MESSAGES/django.po`` in place — merging the
    hand-written catalogues and stamping fuzzy guesses across them. Copying
    the source into a temp dir (6 MB of Python and templates; the heavy
    directories are skipped) makes that impossible by construction rather
    than by flag discipline, and the copy's own empty ``locale/`` gives a
    pure extraction with nothing merged in.
    """
    if shutil.which("xgettext") is None:
        sys.exit(
            "check_messages: xgettext not found.\n"
            "  This guard shells out to Django's makemessages, which needs GNU\n"
            "  gettext. Install it (Debian/Ubuntu: apt-get install gettext), or\n"
            "  run the guard inside the backend container, which already has it:\n"
            "    podman exec tryggare_web_1 sh -c "
            "'cd /app && uv run python scripts/check_messages.py'"
        )

    skip = shutil.ignore_patterns(
        ".venv",
        ".git",
        "staticfiles",
        "dist",
        "node_modules",
        "test-results",
        "locale",
        "__pycache__",
        "*.pyc",
    )

    with tempfile.TemporaryDirectory(prefix="check_messages_") as tmp:
        work = Path(tmp) / "backend"
        shutil.copytree(BACKEND_DIR, work, ignore=skip, symlinks=True)
        (work / "locale").mkdir()

        env = dict(os.environ)
        # SQLite fallback + EMAIL_DISABLED_ACK, so extraction needs neither a
        # database nor mail configuration to get through django.setup().
        env["DJANGO_SETTINGS_MODULE"] = "config.settings.unit"
        env["EMAIL_DISABLED_ACK"] = "true"
        env["PYTHONPATH"] = str(work)

        command = [
            sys.executable,
            "manage.py",
            "makemessages",
            "--locale",
            "sv",
            "--no-obsolete",
            "--no-location",
        ]
        for name in IGNORE:
            command += ["--ignore", name]

        result = subprocess.run(
            command, cwd=str(work), env=env, capture_output=True, text=True
        )
        if result.returncode != 0:
            sys.exit(
                "check_messages: extraction failed.\n"
                + (result.stderr or result.stdout)
            )

        extracted = work / "locale" / "sv" / "LC_MESSAGES" / "django.po"
        if not extracted.exists():
            sys.exit("check_messages: extraction produced no .po file.")
        return {e.msgid for e in parse_po(extracted)}


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    extracted = extract_msgids()
    if not extracted:
        print(
            "check_messages: extraction found no translatable strings — the "
            "guard would be a no-op.",
            file=sys.stderr,
        )
        return 1

    for language in LANGUAGES:
        po_path = LOCALE_DIR / language / "LC_MESSAGES" / "django.po"
        if not po_path.exists():
            failures.append(f"[{language}] catalogue missing: {po_path}")
            continue

        entries = parse_po(po_path)
        by_id = {e.msgid: e for e in entries}

        # Rule 1: every extracted msgid must be present.
        for msgid in sorted(extracted - set(by_id)):
            failures.append(
                f"[{language}] missing msgid: {msgid!r}\n"
                f"         present in the source but not in "
                f"locale/{language}/LC_MESSAGES/django.po"
            )

        for msgid in sorted(by_id):
            entry = by_id[msgid]
            # Rule 3: fuzzy is a guess, not a translation.
            if entry.fuzzy:
                failures.append(
                    f"[{language}] fuzzy entry: {msgid!r}\n"
                    f"         gettext guessed this translation — confirm it "
                    f"and remove the '#, fuzzy' flag"
                )
            # Rule 2: empty msgstr. Rule 4 (msgstr == msgid) is deliberately
            # NOT a failure.
            if not entry.msgstr:
                failures.append(
                    f"[{language}] empty msgstr: {msgid!r}\n"
                    f"         untranslated in "
                    f"locale/{language}/LC_MESSAGES/django.po"
                )
            # Rule 6: invisible characters in the msgstr. Checked on the
            # msgstr only — a msgid is source text the translator may need to
            # mirror. Naming the codepoint and its offset is the whole point:
            # you cannot see the character, so "it's in here somewhere" would
            # just move the puzzle.
            for offset, name in find_invisible(entry.msgstr):
                failures.append(
                    f"[{language}] invisible character in msgstr: {msgid!r}\n"
                    f"         {name} at character offset {offset} of "
                    f"{entry.msgstr!a}\n"
                    f"         it renders as nothing (or as a plain space) but "
                    f"breaks search, sorting and copy-paste — delete it, or "
                    f"replace it with the ordinary character it imitates"
                )

        for msgid in sorted(set(by_id) - extracted):
            warnings.append(f"[{language}] stale msgid no longer in source: {msgid!r}")

    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)

    if failures:
        print(
            f"\n✗ Translation catalogues are stale ({len(failures)} problem(s)):\n",
            file=sys.stderr,
        )
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        print(
            "\nFix: regenerate and fill in the catalogues, then re-run.\n"
            "  podman exec tryggare_web_1 sh -c 'cd /app && "
            "EMAIL_DISABLED_ACK=true uv run python manage.py makemessages "
            "-l sv -l en --no-obsolete --no-location "
            "-i staticfiles -i dist -i node_modules -i tests'\n"
            "Then translate every empty msgstr in locale/sv, mirror the msgid "
            "into locale/en, and clear every '#, fuzzy' flag.\n"
            "An invisible-character failure needs no regeneration — edit that "
            "one msgstr at the offset named above.",
            file=sys.stderr,
        )
        return 1

    print(
        f"✓ Translation catalogues in sync "
        f"({len(extracted)} msgids checked against "
        f"{', '.join(LANGUAGES)})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
