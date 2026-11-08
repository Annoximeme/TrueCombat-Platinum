---
title: Eén klein installatieprogramma, elke versie
date: 2026-11-08
summary: Platinum was ooit een zip van bijna 800 MB. Nu is het een installatieprogramma van 7 MB, een launcher die alleen downloadt wat veranderd is, en een knop die je terugbrengt naar elke eerdere release.
image: img/launcher.webp
tag: Launcher
version: 0.32.0
---
Het grootste deel van zijn bestaan betekende Platinum binnenhalen: één grote zip van bijna 800 MB downloaden, hem ergens uitpakken en hopen dat je een handige map koos. Elke update betekende het opnieuw doen. Sinds versie 0.32 is dat voorbij, en in dit artikel leggen we uit wat ervoor in de plaats kwam.

## Zeven megabyte

De download op deze site is nu een klein installatieprogramma, `TrueCombat-Platinum-Setup.exe`. Je kiest waar het spel komt, zet de launcher eventueel in een aparte map, krijgt snelkoppelingen op het bureaublad en in het Startmenu, en het registreert een echt verwijderprogramma in Windows. Het installeert voor jouw Windows-gebruikersaccount.

Het installatieprogramma zelf bevat alleen de launcher. Zodra het klaar is, downloadt de launcher het spel.

## Alleen wat veranderd is

De launcher downloadt via dezelfde updater die hij voor elke patch gebruikt. Elke release heeft een lijst van alle bestanden met hun vingerafdruk. De launcher vergelijkt die lijst met wat er op je schijf staat en downloadt alleen wat ontbreekt of anders is. Een kleine update blijft een kleine download.

Die lijst is ondertekend. De launcher controleert die handtekening voordat hij iets installeert. Heeft iemand onderweg met de lijst geknoeid, dan klopt de handtekening niet meer en weigert de launcher de update. Bestanden die een nieuwere versie niet meer gebruikt, worden opgeruimd, zodat oude restjes geen vreemd gedrag kunnen veroorzaken.

## Elke versie, altijd

De launcher heeft een knop **Versies**. Die toont elke release die de nieuwe updater ondersteunt en laat je er een installeren, elk vanuit zijn eigen ondertekende lijst. Kies je een oudere release, dan blijft de launcher daarop tot je terugschakelt. Eén klik op de nieuwste versie en je bent weer helemaal bij.

Dat helpt in meer situaties dan je zou denken: een clan die voor een wedstrijd iedereen op dezelfde build wil, een speler die het gevoel van toen wil vergelijken met nu, of gewoon een veilige weg terug als een update je ooit problemen geeft.

## Hoe we het testten

Voor de release liepen we de volledige cyclus door op een echte Windows-pc, acht controles in totaal: een stille installatie, de lijst met releases, een verse installatie van het spel, overschakelen naar een oudere release en terug, en verwijderen. Elke run begint met lege mappen en downloadt het hele spel, zo'n drie gigabyte, zodat niets van een vorige run een probleem kan verbergen.

> Eén eerlijke opmerking: het installatieprogramma is nog niet digitaal ondertekend, dus Windows SmartScreen kan de eerste keer een waarschuwing tonen. Kies **Meer informatie** en daarna **Toch uitvoeren**. Download het installatieprogramma altijd van deze website of van onze GitHub-releasepagina.
