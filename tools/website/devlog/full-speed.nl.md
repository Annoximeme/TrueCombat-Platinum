---
title: Terug op volle snelheid
date: 2026-11-07
summary: Maandenlang voelde Platinum een tikje trager dan het spel dat we kennen. De oorzaak bleek één schaalfactor, op de verkeerde plek toegepast.
image: img/map-railhouse.webp
tag: Gameplay
version: 0.32.0
---
Vanaf de eerste publieke builds vertelden veteranen ons hetzelfde: Platinum zag er goed uit, klonk goed, en voelde een tikje te traag. Onze eigen bewegingstests zeiden iets anders. Elke snelheid die we maten klopte met de waarden uit de TC:E-brondata. Beide kanten hadden gelijk, en om te begrijpen waarom moesten we terug het originele spel in.

## Eén factor, twee betekenissen

TrueCombat: Elite 0.49b schaalt de bewegingssnelheid met `g_movespeed / 127`. De standaardwaarde op de server is 76, dus die factor remt spelers af tot ongeveer 60% van hun basissnelheid. Wat we over het hoofd hadden gezien, is waar het origineel hem toepast: alleen in speltype 0 en 1, de oefen- en free-for-allmodi. De modi waarin TC:E echt gespeeld werd, zoals Flag Capture en Bomb, draaien onder andere speltypenummers en raken de factor nooit aan. Daar loop je op volle snelheid.

Platinum laat al zijn modi intern via speltype 0 lopen, dus de vertraging uit de oefenmodus gold overal. Onze tests maten de vertraagde snelheid en vonden die correct.

We hebben het op twee manieren bevestigd: met de snelheidstabel in de originele 0.49b-changelog, en met de constante 1/127 in de originele spelcode. Beide wezen naar hetzelfde antwoord.

## De cijfers

Met een geweer en de standaard serverinstellingen beweeg je in Platinum 0.32 zo snel:

- **238** eenheden per seconde sprintend
- **163** rennend
- **68** gehurkt
- **38** liggend

Dat zijn de originele TC:E-snelheden. De [gids](guide.html) heeft het volledige overzicht.

## Wat volle snelheid blootlegde

Sneller bewegen bracht dingen aan het licht die de lagere snelheid verborg. Andere spelers wisselden op het verkeerde moment tussen hun loop- en renanimatie, dus die grens ligt nu op 150 eenheden per seconde, net als in het origineel.

Het staminasysteem had een subtieler probleem. Een herstelbonus werd elk frame toegepast, ook tijdens het rennen. Op de oude rensnelheid viel dat nooit op, omdat langzaam rennen sowieso als herstellen telde. Op 163 eenheden per seconde zouden spelers stamina terugkrijgen terwijl ze op volle snelheid renden. Herstel gebeurt nu alleen wanneer het hoort: stilstaand, lopend, gehurkt of liggend.

Nu we er toch mee bezig waren, duren Elimination-rondes weer hun originele vijf minuten.

## Waarom het telt

TC:E draait om timing. Hoe lang je erover doet om een straat over te steken, een hoek te bereiken of terug in dekking te komen, is waar elke map omheen gebouwd is. Zit je daar 40% naast, dan verandert elk gevecht op elke map, en geen screenshot laat het zien. Daarom wordt elke snelheid in Platinum nu met de originele data vergeleken voordat een release uitkomt.
