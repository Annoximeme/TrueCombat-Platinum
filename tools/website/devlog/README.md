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

## Body

`##` and `###` headings (three or more `##` headings add an "In this post" list), paragraphs,
`-` and `1.` lists, `**bold**`, `*italic*`, `` `code` ``, `[links](page.html)`, and:

```
> A callout, for the one thing a reader must not miss.

![Alt text](img/devlog/picture.webp "Caption")

!compare(img/devlog/before.webp | High | img/devlog/after.webp | Ultra | Caption)
```

Images go in `docs/img/devlog/`, 1280x720 WebP. The build stops if a referenced image is missing.

## Writing

- Write for players, not developers. Explain what changed, why, and how it was tested.
- Be honest about trade-offs and what is not done yet. That is the point of the devlog.
- Use the house style of the rest of the site: plain, confident, no hype.
- Never publish server addresses other than the public game addresses, internal paths, file names of
  private tools, keys, passwords or anything from a private configuration.
- Do not describe unreleased work as released. Use `version` and keep the body neutral about timing.
