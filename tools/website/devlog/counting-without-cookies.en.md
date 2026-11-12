---
title: Finding new players without tracking anyone
date: 2026-11-12
time: 18:00
summary: TrueCombat: Platinum is about to go public on more platforms than ever. To learn which of them actually bring players, the site now counts visits and downloads the same way it counts devlog readers: no cookies, no outside companies, and nothing that leads back to you.
image: img/map-stadtrand.webp
tag: Community
---
With 0.36.0 we start telling a much bigger audience about TrueCombat: Platinum. ModDB, itch.io, Reddit, creators, the old TC:E crowd. Some of those places will bring players. Some will not. With a small team and limited time, we need to know which is which, so the effort goes where it works.

Earlier this month we explained how the devlog [counts readers without tracking anyone](devlog-reads-and-ratings.html). The site now uses the same approach for the whole website.

## What changes

Every page now tells our own server, once, that someone opened it: the page, the name of the site that linked there, the campaign tag in the link if there is one, the page language, and whether the screen is phone, tablet or desktop size. A click on a download button tells it that a download started.

Links we post on other platforms now go through short addresses such as `truecombat.eu/go/moddb`. They open the normal page with a small campaign tag, which the site reads once and then removes from the address bar, so a link you copy and share stays clean.

## What does not change

- No cookies. Nothing is stored in your browser for counting.
- No Google Analytics, no Meta pixel, no analytics company of any kind.
- No IP addresses kept. The server uses your connection for one moment to count you once per day, then the daily secret behind that count is deleted at midnight, together with everything made with it.
- Global Privacy Control and Do Not Track are respected. With either switched on, you are not counted at all.

What remains is a set of daily totals: this many people opened the maps page, this many came from ModDB, this many of them downloaded the game. That is enough to make good decisions and not enough to say anything about any one of you.

## Where to read the details

Everything we count, on the website and in the game, is now listed in one place: the new [privacy page](privacy.html), in all five site languages. If we ever count something new, that page changes first and the devlog says so.

## What is next

The launcher will get an optional switch to share anonymous performance and crash data, so we can see which graphics cards and drivers need attention before a playtest tells us. It will be off unless you turn it on, and it is planned for the update after 0.36.0. We will post the full list of what it sends before it ships.

The code that does the counting is in the public repository, next to the stats service. As always, you never have to take our word for it.
