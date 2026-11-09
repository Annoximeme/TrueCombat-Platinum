---
title: Counting readers without tracking anyone
date: 2026-11-09
time: 18:00
summary: Every devlog post now ends with a star rating, and we can finally see which posts people read. Here is how we built that without cookies, without analytics and without storing anything that points back to you.
image: img/map-northport.webp
tag: Community
---
From the first day, this website has had one firm rule: no visitor tracking. No analytics scripts, no cookies, no third-party embeds that load before you click them. That rule is not changing.

It did leave us writing the devlog in the dark, though. We had no idea which posts were worth the time, which ones people gave up on halfway, and which topics you want more of. So we built the smallest thing that answers those questions and nothing else.

## What you will notice

At the end of every post there is now one question: **was this worth the read?** Pick one to five stars. You can change your mind until the end of the day, and you never need an account.

Once a post has five ratings, its average appears next to the date on the devlog. Below five, a single early vote would say more about that one reader than about the post, so we keep it to ourselves until there is enough to go on.

## What we count, and what we do not

When a post has been open on your screen for ten seconds, your browser sends one message to our own server: *someone read this post*. If you then reach the end of the post, it sends one more: *someone finished it*. That is the entire signal. Nothing is sent when you just open a page and leave.

To count a reader once instead of every time they reload, the server needs to recognise a repeat visit for one day. It does that with a one-way fingerprint made from your connection and the post, mixed with a random secret that only exists for that day. At midnight the secret and every fingerprint are deleted. After that, nobody can work out who read what, including us.

What we keep, permanently, is a handful of numbers per post per day: how many people read it, how many finished it, and how many stars it received.

What we never keep:

- IP addresses, browser details or device information
- Cookies, of any kind
- Anything from Google, Meta or any other analytics company
- Any link between a rating and the person who gave it

> Your star rating is remembered in your own browser only, so the stars stay filled in when you come back. That note never leaves your computer.

## Why read counts are not public yet

The numbers are visible to the studio only, for now. A brand-new devlog with small numbers next to every post tells a visitor very little, and we would rather show them once they mean something. When that happens, it is a single switch on our side.

## Keeping it fair

Ratings are open to everyone, so they need some protection. Each reader gets one rating per post per day, a second vote replaces the first, and the server slows down anyone who sends far more requests than a person reading a page ever would. Search engine crawlers are ignored entirely.

As always, if you have questions about how any of this works, ask us on Discord. The code that does the counting is part of the public repository, so you never have to take our word for it.
