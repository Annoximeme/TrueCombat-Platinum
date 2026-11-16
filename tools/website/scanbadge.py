"""Virus scan and checksum blocks for the download buttons, the download page and the release pages.

The data comes from tools/website/scans.json, which tools/release/virusscan.py keeps current
(GitHub Actions, on every release and once a day). A release without a finished scan shows
its checksum only; a release without an entry shows nothing, so the site never claims a scan
that did not happen. Detections are shown as they are, with the full report a click away.
"""
import html as htmlmod
import json
import pathlib
import re

STORE = pathlib.Path(__file__).resolve().parent / "scans.json"
SETUP = "TrueCombat-Platinum-Setup.exe"

SHIELD = ('<svg class="scan-ico" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
          'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l7 3v5c0 4.6-3 8.4-7 10-4-1.6-7-5.4-7-10V6z"/>'
          '<path class="tick" d="M8.8 12.2l2.2 2.2 4.4-4.6"/></svg>')

T = {
    "en": {
        "h_plain": "Verify your download",
        "ok_b": "Scanned clean", "ok_s": "0/{n} antivirus engines",
        "flag_b": "Antivirus scan", "flag_s": "{f}/{n} engines flag it",
        "tip": "Open the VirusTotal report for this installer",
        "eyebrow": "Download safety", "h": "Scanned, and verifiable",
        "ok": "Every release is checked with VirusTotal before it reaches you. {n} antivirus engines scanned this installer, and none of them flags it.",
        "flag": "Every release is checked with VirusTotal before it reaches you. {f} of {n} antivirus engines flag this installer. New games without a code-signing certificate are sometimes flagged by mistake, so we publish the full report: it shows exactly which engines raised a flag.",
        "files_ok": "The {k} program files the launcher installs are scanned as well. None of them is flagged.",
        "files_flag": "The {k} program files the launcher installs are scanned as well: {fk} of them are flagged by at least one engine.",
        "plain": "Check that your copy of the installer is exactly the file we published.",
        "report": "Full VirusTotal report",
        "sha": "SHA-256 checksum", "copy": "Copy",
        "how": "To confirm your copy is the one we published, run <code>Get-FileHash TrueCombat-Platinum-Setup.exe</code> in PowerShell and compare the result with the checksum above.",
        "checked": "Last checked {d}",
    },
    "nl": {
        "h_plain": "Controleer je download",
        "ok_b": "Virusvrij gescand", "ok_s": "0/{n} antivirusscanners",
        "flag_b": "Virusscan", "flag_s": "{f}/{n} scanners geven een melding",
        "tip": "Open het VirusTotal-rapport van dit installatieprogramma",
        "eyebrow": "Veilig downloaden", "h": "Gescand en controleerbaar",
        "ok": "Elke release controleren we met VirusTotal voordat hij bij jou terechtkomt. {n} antivirusscanners hebben dit installatieprogramma gescand, en geen enkele geeft een melding.",
        "flag": "Elke release controleren we met VirusTotal voordat hij bij jou terechtkomt. {f} van de {n} antivirusscanners geven een melding bij dit installatieprogramma. Nieuwe games zonder certificaat voor codeondertekening worden soms ten onrechte gemarkeerd, daarom publiceren we het volledige rapport: daarin zie je precies welke scanners een melding geven.",
        "files_ok": "De {k} programmabestanden die de launcher installeert, scannen we ook. Geen enkel bestand geeft een melding.",
        "files_flag": "De {k} programmabestanden die de launcher installeert, scannen we ook: bij {fk} daarvan geeft minstens één scanner een melding.",
        "plain": "Controleer of jouw installatieprogramma precies het bestand is dat wij publiceerden.",
        "report": "Volledig VirusTotal-rapport",
        "sha": "SHA-256-controlegetal", "copy": "Kopiëren",
        "how": "Wil je zeker weten dat je exemplaar het onze is? Voer <code>Get-FileHash TrueCombat-Platinum-Setup.exe</code> uit in PowerShell en vergelijk de uitkomst met het controlegetal hierboven.",
        "checked": "Laatst gecontroleerd op {d}",
    },
    "de": {
        "h_plain": "Prüfe deinen Download",
        "ok_b": "Virenfrei geprüft", "ok_s": "0/{n} Virenscanner",
        "flag_b": "Virenscan", "flag_s": "{f}/{n} Scanner melden etwas",
        "tip": "VirusTotal-Bericht zu diesem Installer öffnen",
        "eyebrow": "Sicher herunterladen", "h": "Geprüft und nachprüfbar",
        "ok": "Jede Version prüfen wir mit VirusTotal, bevor sie bei dir ankommt. {n} Virenscanner haben diesen Installer geprüft, und keiner schlägt an.",
        "flag": "Jede Version prüfen wir mit VirusTotal, bevor sie bei dir ankommt. {f} von {n} Virenscannern schlagen bei diesem Installer an. Neue Spiele ohne Codesignatur-Zertifikat werden manchmal fälschlich markiert, deshalb veröffentlichen wir den vollständigen Bericht: Er zeigt genau, welche Scanner anschlagen.",
        "files_ok": "Die {k} Programmdateien, die der Launcher installiert, prüfen wir ebenfalls. Keine davon wird gemeldet.",
        "files_flag": "Die {k} Programmdateien, die der Launcher installiert, prüfen wir ebenfalls: {fk} davon meldet mindestens ein Scanner.",
        "plain": "Prüfe, ob dein Installer genau die Datei ist, die wir veröffentlicht haben.",
        "report": "Vollständiger VirusTotal-Bericht",
        "sha": "SHA-256-Prüfsumme", "copy": "Kopieren",
        "how": "Um sicherzugehen, dass deine Kopie unsere ist, führe <code>Get-FileHash TrueCombat-Platinum-Setup.exe</code> in PowerShell aus und vergleiche das Ergebnis mit der Prüfsumme oben.",
        "checked": "Zuletzt geprüft am {d}",
    },
    "fr": {
        "h_plain": "Vérifiez votre téléchargement",
        "ok_b": "Analysé, aucune menace", "ok_s": "0/{n} antivirus",
        "flag_b": "Analyse antivirus", "flag_s": "{f}/{n} antivirus le signalent",
        "tip": "Ouvrir le rapport VirusTotal de cet installateur",
        "eyebrow": "Téléchargement sûr", "h": "Analysé et vérifiable",
        "ok": "Chaque version est analysée par VirusTotal avant de vous parvenir. {n} antivirus ont analysé cet installateur, et aucun ne le signale.",
        "flag": "Chaque version est analysée par VirusTotal avant de vous parvenir. {f} antivirus sur {n} signalent cet installateur. Les jeux récents sans certificat de signature de code sont parfois signalés par erreur, c'est pourquoi nous publions le rapport complet : il indique précisément quels antivirus ont réagi.",
        "files_ok": "Les {k} fichiers du programme installés par le launcher sont analysés eux aussi. Aucun n'est signalé.",
        "files_flag": "Les {k} fichiers du programme installés par le launcher sont analysés eux aussi : {fk} d'entre eux sont signalés par au moins un antivirus.",
        "plain": "Vérifiez que votre installateur est exactement le fichier que nous avons publié.",
        "report": "Rapport VirusTotal complet",
        "sha": "Somme de contrôle SHA-256", "copy": "Copier",
        "how": "Pour vous assurer que votre copie est bien la nôtre, lancez <code>Get-FileHash TrueCombat-Platinum-Setup.exe</code> dans PowerShell et comparez le résultat avec la somme ci-dessus.",
        "checked": "Dernière vérification le {d}",
    },
    "pl": {
        "h_plain": "Sprawdź pobrany plik",
        "ok_b": "Przeskanowany, czysty", "ok_s": "0/{n} programów antywirusowych",
        "flag_b": "Skan antywirusowy", "flag_s": "{f}/{n} programów zgłasza plik",
        "tip": "Otwórz raport VirusTotal dla tego instalatora",
        "eyebrow": "Bezpieczne pobieranie", "h": "Przeskanowany i do sprawdzenia",
        "ok": "Każde wydanie sprawdzamy w VirusTotal, zanim do ciebie trafi. Ten instalator przeskanowało {n} programów antywirusowych i żaden go nie zgłasza.",
        "flag": "Każde wydanie sprawdzamy w VirusTotal, zanim do ciebie trafi. {f} z {n} programów antywirusowych zgłasza ten instalator. Nowe gry bez certyfikatu podpisywania kodu bywają oznaczane omyłkowo, dlatego publikujemy pełny raport: widać w nim dokładnie, które programy zgłosiły plik.",
        "files_ok": "Skanujemy też {k} plików programu instalowanych przez launcher. Żaden nie jest zgłaszany.",
        "files_flag": "Skanujemy też {k} plików programu instalowanych przez launcher: {fk} z nich zgłasza co najmniej jeden program.",
        "plain": "Sprawdź, czy twój instalator to dokładnie ten plik, który opublikowaliśmy.",
        "report": "Pełny raport VirusTotal",
        "sha": "Suma kontrolna SHA-256", "copy": "Kopiuj",
        "how": "Aby upewnić się, że twoja kopia jest nasza, uruchom w PowerShell <code>Get-FileHash TrueCombat-Platinum-Setup.exe</code> i porównaj wynik z sumą powyżej.",
        "checked": "Ostatnio sprawdzono {d}",
    },
}

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def _load():
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"files": {}, "releases": {}}


def info(version):
    """The scan of a release, by tag (v0.37.3-sandbox33) or by version (v0.37.3). None when there is none."""
    data = _load()
    rels = data.get("releases", {})
    tag = version if version in rels else next((t for t in rels if t.startswith(version + "-") and not rels[t].get("draft")), None)
    if not tag:
        return None
    rel = rels[tag]
    files = data["files"]
    setup = files.get(rel["setup"], {})
    # the program files the launcher installs; the installer itself is reported on its own
    shas = list(dict.fromkeys(sha for name, sha in rel["files"].items() if name != SETUP))
    scanned = [files[s] for s in shas if "engines" in files.get(s, {}) and not files[s].get("pending")]
    flag = lambda f: f.get("malicious", 0) + f.get("suspicious", 0)
    out = {"tag": tag, "sha": rel["setup"], "report": "https://www.virustotal.com/gui/file/" + rel["setup"],
           "scanned": "engines" in setup and not setup.get("pending"), "files": len(shas),
           "files_done": len(scanned) == len(shas), "files_flagged": sum(1 for f in scanned if flag(f)),
           "checked": max((f.get("checked", "") for f in scanned), default="")}
    if out["scanned"]:
        out.update(flagged=flag(setup), engines=setup["engines"])
    return out


def _date(iso_text):
    if not iso_text:
        return ""
    return "%d %s %s" % (int(iso_text[8:10]), MONTHS[int(iso_text[5:7]) - 1], iso_text[:4])


def chip(lang, s):
    """The small badge that sits beside a download button. Empty until the installer has been scanned."""
    if not s or not s["scanned"]:
        return ""
    L = T.get(lang, T["en"])
    ok = s["flagged"] == 0
    b = L["ok_b" if ok else "flag_b"]
    small = L["ok_s" if ok else "flag_s"].format(n=s["engines"], f=s["flagged"])
    return ('<a class="scan-chip%s" data-scan="%s" href="%s" target="_blank" rel="noopener" title="%s">%s'
            '<span class="stack"><b>%s</b><small>%s</small></span></a>') % (
        "" if ok else " is-flagged", htmlmod.escape(s["tag"]), s["report"], htmlmod.escape(L["tip"]), SHIELD, b, small)


def marked(name, lang, s, indent="      "):
    """chip() between <!--name--> markers, for the hand-edited home page."""
    c = chip(lang, s)
    return "<!--%s-->%s<!--/%s-->" % (name, ("\n" + indent + c + "\n" + indent) if c else "", name)


def sha_row(lang, s):
    L = T.get(lang, T["en"])
    return ('<div class="sha-row" data-scan="%s"><span class="sha-label">%s</span><code class="sha">%s</code>'
            '<button type="button" class="btn btn-ghost sha-copy" data-copy="%s">%s</button></div>') % (
        htmlmod.escape(s["tag"]), L["sha"], s["sha"], s["sha"], L["copy"])


def panel(lang, s, month_fmt=None):
    """The download page section: scan result, program files, checksum and how to check it."""
    if not s:
        return ""
    L = T.get(lang, T["en"])
    if s["scanned"]:
        lede = L["ok" if s["flagged"] == 0 else "flag"].format(n=s["engines"], f=s["flagged"])
        if s["files_done"] and s["files"] > 1:
            lede += " " + L["files_ok" if s["files_flagged"] == 0 else "files_flag"].format(k=s["files"], fk=s["files_flagged"])
        report = '<a class="btn btn-ghost" href="%s" target="_blank" rel="noopener">%s ↗</a>' % (s["report"], L["report"])
        checked = L["checked"].format(d=(month_fmt or (lambda x: x))(_date(s["checked"]))) if s["checked"] else ""
    else:
        lede, report, checked = L["plain"], "", ""
    title = L["h"] if s["scanned"] else L["h_plain"]
    return f"""<section class="band band-alt scan-panel" id="safety" data-scan="{htmlmod.escape(s['tag'])}">
  <div class="wrap scan-grid">
    <div>
      <span class="eyebrow">{L['eyebrow']}</span>
      <h2>{title}</h2>
      <p class="lede">{lede}</p>
      {'<div class="hero-cta">' + report + ('<span class="scan-when">' + checked + '</span>' if checked else '') + '</div>' if report else ''}
    </div>
    <div class="scan-sha">
      {sha_row(lang, s)}
      <p>{L['how']}</p>
    </div>
  </div>
</section>"""


def release_row(s):
    """The check on a release page (English only, like the release pages)."""
    if not s:
        return ""
    return '<div class="rel-scan">%s%s</div>' % (chip("en", s), sha_row("en", s))


def version_of(tag):
    m = re.match(r"^v?(\d+\.\d+\.\d+)", tag)
    return "v" + m.group(1) if m else tag
