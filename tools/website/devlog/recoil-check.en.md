---
title: When the test is wrong
date: 2026-11-08
summary: Our recoil checks flagged the Desert Eagle as broken. The game was right. Here is how we found out, and why we would rather chase a false alarm than miss a real one.
image: img/media-soldier-hd.webp
tag: Testing
---
Platinum is a rebuild of TrueCombat: Elite, so "it feels about right" is never good enough. Every weapon is checked against the original game: damage, fire rate, spread, and how the view kicks and recovers when you shoot. Those checks run automatically, on DirectX 12 and on OpenGL, before every release.

## The red light

During routine testing for the next update, the recoil check failed on one weapon. Fired from the hip, the Desert Eagle did not settle back where the check expected. After every shot the view ended up a little higher than it should, and over a magazine that added up to a clear difference.

A result like that is never ignored. Recoil is part of what makes each weapon what it is, and the Desert Eagle is a weapon people have strong memories of.

## Back to the original

So we went back to the original game and traced exactly what happens when a shot is fired. Every shot has a kick: how far the view is pushed up. The original game moves your view by the full kick, but it limits how much of that kick it will later pull back down.

For most weapons the limit never matters, because their kick is smaller than the cap. The Desert Eagle fired from the hip is the exception. Its kick is larger than the limit, so each shot leaves a small, permanent climb that the recovery never takes back. That is how the original behaves, and it is part of why a hip-fired Deagle feels the way it does.

Platinum already did exactly the same. The check did not: it assumed the full kick would be recovered.

## Fixing the right thing

We changed the check, not the game. With the cap included, the Desert Eagle passes on DirectX 12, on OpenGL, and against the current release.

> No gameplay change came out of this. If you were worried the Deagle would be "fixed" into something it never was, it will not be.

## Why we tell you this

A post about a test that was wrong might seem like an odd thing to publish. We think it shows how Platinum is made. Every value is compared to the original, every difference is investigated before anything changes, and sometimes the investigation proves the game right. A false alarm costs us an afternoon. A real difference that slips through costs every player who remembers how the weapon should feel.
