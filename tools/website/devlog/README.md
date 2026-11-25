# Devlog

Every post is two files: `<slug>.en.md` and `<slug>.nl.md`. `python tools/website/build.py`
turns them into `docs/devlog-<slug>.html`, `docs/nl/devlog-<slug>.html`, the post list and topic
filter on `devlog.html`, the latest-post card on the home page, both Atom feeds and the sitemap.
Run `python tools/website/og.py` afterwards for the share image (`docs/img/og-devlog-<slug>.jpg`).

## Front matter

```
---
title: New light for old maps
date: 2026-11-08
summary: One or two sentences. Shown on the card, in the feed and in link previews.
image: img/devlog/ultra-railhouse-ultra.webp
tag: Graphics
version: 0.33.0
---
```

- `image` must exist in `docs/` together with its `-640.webp` version.
- `tag` is the topic filter. Reuse an existing tag where one fits (the Dutch file uses the Dutch tag).
- `version` is optional. It ties the post to a release. While that version is newer than the one on the
  download button, the post shows "Next update · in testing". The build after the release is published
  (the Website workflow runs on every release) turns it into "Shipped in vX.Y.Z" by itself, so a post
  about upcoming work never claims a release that has not happened.
- `updated: YYYY-MM-DD` is optional, for a post that was revised later.
- `time: HH:MM` is optional. Posts from the same day are listed newest time first (no time counts as 00:00).
- `kicker: Update 0.38.0` is optional and marks a post about a major update or patch. The newest post with a
  kicker takes the big spot on the home page and at the top of `devlog.html`, and its own page opens on the
  `image` at full size with the kicker above the title. Give these posts clean teaser art as `image` (no logo or
  text, see `teaser.py`); a `-1920.webp` next to it is used on wide screens when it exists. Without any kicker
  post, the newest post takes the spot.
- The newest post always sits in the home page hero as a card beside the game. When that post has a kicker,
  its `image` also opens the hero slideshow for 14 days from `date`; after that the map slides return by
  themselves, and the next site build drops it from the page.
- `comments: off` is optional and leaves the comment section off that post. Every other post gets one: signed-in
  players comment, reply, like and report; the team moderates on the staff portal's Devlog comments page. The
  section stays hidden while the account service is down. English and Dutch pages share one comment thread.

## Body

`##` and `###` headings (three or more `##` headings add an "In this post" list), paragraphs,
`-` and `1.` lists, `**bold**`, `*italic*`, `` `code` ``, `[links](page.html)`, and:

```
> A callout, for the one thing a reader must not miss.

![Alt text](img/devlog/picture.webp "Caption")

!compare(img/devlog/before.webp | High | img/devlog/after.webp | Ultra | Caption)
```

Images go in `docs/img/devlog/`, 1280x720 WebP. The build stops if a referenced image is missing.
The build strips EXIF, XMP and C2PA "Content Credentials" metadata from every image in `docs/` (pixels stay
identical), and `check_site.py` fails on any image that still carries it. Images copied through shared drives and
editing tools often pick it up; `python tools/strip_image_metadata.py <files or folders>` cleans them anywhere,
including game and launcher assets before packaging.

## Writing

- Write for players, not developers. Explain what changed, why, and how it was tested.
- Be honest about trade-offs and what is not done yet. That is the point of the devlog.
- Use the house style of the rest of the site: plain, confident, no hype.
- Never publish server addresses other than the public game addresses, internal paths, file names of
  private tools, keys, passwords or anything from a private configuration.
- Do not describe unreleased work as released. Use `version` and keep the body neutral about timing.
