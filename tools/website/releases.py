"""Release pages: one page per version, release-<x-y-z>.html, built from the patch notes that
release_sync.py bakes into news.html. English only, like the patch notes themselves.

build.py calls:
  parse(news_html)            -> releases, newest first
  page_body(rel, rels, posts) -> the <main> body of one release page
  link_blocks(lang, html)     -> adds a "Release page" link inside every patch-notes block on a page
"""
import html as htmlmod
import re

MEDIA = ["media-village-hd", "media-deployment", "map-railhouse", "media-grenade", "map-northport",
         "media-village-yard", "map-snow", "map-delta", "map-stadtrand", "media-map-vote", "media-soldier-hd"]

LINK = {"en": "Release page", "nl": "Releasepagina", "de": "Release-Seite", "fr": "Page de la version", "pl": "Strona wydania"}

BLOCK = re.compile(r'<details class="release" id="([^"]+)" data-ver="([^"]+)"[^>]*>(.*?)</details>', re.S)


def slug(ver):
    """v0.35.0 -> release-0-35-0"""
    return "release-" + ver.lstrip("v").replace(".", "-")


def strip(s):
    return re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def parse(news):
    rels = []
    for m in BLOCK.finditer(news):
        inner = m.group(3)
        summ = re.search(r'<span class="sum">(.*?)</span>', inner, re.S)
        meta = re.search(r'<span class="meta">(.*?)<svg', inner, re.S)
        meta_t = strip(meta.group(1)) if meta else ""
        date = re.search(r"(\d{1,2} [A-Z][a-z]{2} \d{4})", meta_t)
        sections = []
        for s in re.finditer(r"<section><h3>(.*?)</h3><ul>(.*?)</ul></section>", inner, re.S):
            items = [i.strip() for i in re.findall(r"<li>(.*?)</li>", s.group(2), re.S)]
            sections.append({"title": s.group(1).strip(), "items": items})
        gh = re.search(r'<p class="rel-link"><a href="([^"]+)"', inner)
        rels.append({"ver": m.group(2), "id": m.group(1), "summary": summ.group(1).strip() if summ else "",
                     "meta": meta_t, "date": date.group(1) if date else "", "sections": sections,
                     "github": gh.group(1) if gh else None, "page": slug(m.group(2))})
    return [r for r in rels if r["sections"]]


def art(rel, rels, posts):
    """The release's image: the devlog post written for that version, else a screenshot by position."""
    v = rel["ver"].lstrip("v")
    for p in posts:
        if p.get("version", "").strip() == v:
            return p["image"].replace(".webp", ""), p
    i = [r["ver"] for r in rels].index(rel["ver"])
    return "img/" + MEDIA[i % len(MEDIA)], None


def page_body(rel, rels, posts, gh_repo):
    e = lambda t: htmlmod.escape(t, quote=True)
    i = [r["ver"] for r in rels].index(rel["ver"])
    newer = rels[i - 1] if i > 0 else None
    older = rels[i + 1] if i + 1 < len(rels) else None
    image, post = art(rel, rels, posts)
    count = sum(len(s["items"]) for s in rel["sections"])
    latest = i == 0
    actions = ['<a class="btn" href="download.html">Download the latest version</a>' if latest else
               '<a class="btn btn-ghost" href="%s">Download this version</a>' % e(rel["github"] or "%s/releases/tag/%s" % (gh_repo, rel["ver"]))]
    if post:
        actions.append('<a class="btn btn-ghost" href="devlog-%s.html">Read the devlog</a>' % post["slug"])
    actions.append('<a class="btn btn-ghost" href="news.html#%s">All patch notes</a>' % e(rel["id"]))
    glance = "\n".join(
        '      <li><a href="#%s"><b>%s</b><span>%d %s</span><p>%s</p></a></li>' % (
            "s-" + re.sub(r"[^a-z0-9]+", "-", strip(s["title"]).lower()).strip("-"), s["title"], len(s["items"]),
            "change" if len(s["items"]) == 1 else "changes", e(strip(s["items"][0])[:150].rsplit(" ", 1)[0] + ("…" if len(strip(s["items"][0])) > 150 else "")))
        for s in rel["sections"][:6])
    notes = "\n".join(
        '    <section class="rel-sec" id="%s"><h2>%s</h2><ul>\n%s\n    </ul></section>' % (
            "s-" + re.sub(r"[^a-z0-9]+", "-", strip(s["title"]).lower()).strip("-"), s["title"],
            "\n".join("      <li>%s</li>" % it for it in s["items"]))
        for s in rel["sections"])
    pager = []
    if older:
        pager.append('<a class="rel-prev" href="%s.html"><span>Previous release</span><b>%s</b></a>' % (older["page"], older["ver"]))
    if newer:
        pager.append('<a class="rel-next" href="%s.html"><span>Next release</span><b>%s</b></a>' % (newer["page"], newer["ver"]))
    body = f"""<section class="page-head rel-head">
  <div class="head-art" style="--art: url({image}.webp); --art-s: url({image}-640.webp)" aria-hidden="true"></div>
  <div class="wrap">
    <a class="pf-back" href="news.html">← Patch notes</a>
    <span class="eyebrow">Release{' · Latest' if latest else ''}{' · ' + rel['date'] if rel['date'] else ''}</span>
    <h1>TrueCombat: Platinum {rel["ver"].lstrip("v")}</h1>
    <p class="lede">{rel['summary']}</p>
    <p class="rel-facts"><span>{count} changes</span><span>{len(rel['sections'])} areas</span><span>{e(rel['meta'])}</span></p>
    <div class="hero-cta">{''.join(actions)}</div>
  </div>
</section>

<section class="band rel-glance">
  <div class="wrap">
    <h2 class="eyebrow">At a glance</h2>
    <ul class="rel-cards">
{glance}
    </ul>
  </div>
</section>

<section class="band band-alt rel-notes">
  <div class="wrap">
{notes}
    <nav class="rel-pager" aria-label="Other releases">{''.join(pager)}</nav>
  </div>
</section>
"""
    title = "TrueCombat: Platinum %s · Release notes" % rel["ver"]
    desc = strip(rel["summary"]) or "Everything that changed in TrueCombat: Platinum %s." % rel["ver"]
    return title, desc, body


def link_blocks(lang, html, up=""):
    """Adds (or refreshes) a link to the release page at the end of every patch-notes block."""
    html = re.sub(r'\n?[ \t]*<p class="rel-page">.*?</p>', "", html)

    def one(m):
        block = m.group(0)
        link = '\n          <p class="rel-page"><a href="%s%s.html">%s →</a></p>' % (up, slug(m.group(2)), LINK.get(lang, LINK["en"]))
        return re.sub(r"(\n\s*</div>\s*</details>)$", lambda x: link + x.group(1), block, count=1)
    return BLOCK.sub(one, html)
