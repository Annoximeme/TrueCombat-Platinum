"""The site's extra languages (German, French, Polish).

English is the source and Dutch has its own strict pair file (nl.py). Each language here is a
module with three things, all optional and all falling back to English when something is missing,
so a new English sentence never breaks the build for these languages:

  PAIRS   {english text: translation}. The keys are the English halves of the pairs in nl.py, plus
          loose strings such as weapon names, map descriptions and roadmap items.
  TABLES  {table name: {key: translation}} for the string tables in build.py, landing.py and
          detail.py (LABELS, WL, DOWNLOAD_T, S and so on).
  JS      strings for docs/js/site.js, written to docs/js/lang-<code>.js.

Pages listed in EN_ONLY are not translated: their links lead to the English page.
"""
import importlib

LANGS = ["de", "fr", "pl"]
NAMES = {"en": "English", "nl": "Nederlands", "de": "Deutsch", "fr": "Français", "pl": "Polski"}
OGLOCALE = {"de": "de_DE", "fr": "fr_FR", "pl": "pl_PL"}
EN_ONLY = ("news", "devlog", "press", "studio", "support", "account")

MODS = {code: importlib.import_module("i18n." + code) for code in LANGS}


def tx(lang, text):
    """A loose string in the given language, or the English when there is no translation."""
    mod = MODS.get(lang)
    return mod.PAIRS.get(text, text) if mod else text


def merge(en, over):
    """en with the translated keys laid over it; nested tables merge the same way."""
    if isinstance(en, dict):
        out = dict(en)
        for k, v in (over or {}).items():
            out[k] = merge(en[k], v) if k in en and isinstance(en[k], dict) else v
        return out
    return over if over else en


def extend(table, name):
    """Adds an entry per extra language to a {"en": ..., "nl": ...} table."""
    for code, mod in MODS.items():
        table[code] = merge(table["en"], getattr(mod, "TABLES", {}).get(name))
    return table
