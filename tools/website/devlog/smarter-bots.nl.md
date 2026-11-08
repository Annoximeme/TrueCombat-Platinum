---
title: Bots leren spelen als mensen
date: 2026-11-08
summary: Bots die nooit missen zijn niet leuk, en bots die het doel negeren zijn nog erger. Zo testen we elke wijziging aan de bots van Platinum voordat die op een server komt.
image: img/media-village-yard.webp
tag: Bots
version: 0.33.0
---
TC:E heeft nooit bots gehad. Platinum wel, want een tactische shooter is alleen leuk als er genoeg mensen zijn om tegen te spelen, en een lege server blijft leeg. Onze tweede officiële server draait daarom met tien bots. Dat legt veel gewicht op ze: een slechte bot leert nieuwe spelers verkeerde gewoontes aan, en een perfecte bot is gewoon frustrerend.

## Beginnen bij nul

De originele maps bevatten helemaal geen gegevens voor bots. Er staat nergens waar een speler kan lopen, springen of klimmen. De eerste klus was dus een navigatiesysteem dat bij het laden de geometrie van elke map leest en zelf de routes uitwerkt: vloeren, trappen, randen, deuren, ladders en water. Op onze maps duurt dat tussen een halve en anderhalve seconde.

Daarmee op zijn plek gaf versie 0.31 de bots de basis: bewegen, schieten, granaten gooien, liggen en om hoeken kijken. Versie 0.32 leerde ze het doel. Bots planten en ontmantelen nu de bom, brengen de vlag naar huis en nemen het veroverpunt in, en ze melden in de teamchat wat ze doen.

## Menselijk maken

De ronde die nu in test is, gaat over *hoe* bots vechten. Een paar van de wijzigingen:

- **Reactietijd** hangt af van de situatie. Een vijand recht vooruit wordt sneller opgemerkt dan een aan de rand van het beeld.
- **Richten** gaat niet meer met een ruk. Een bot zwiept naar een doel, schiet er net over of net onder, en komt tot rust. Een bewegende speler volgen gaat net traag genoeg om eerlijk te voelen.
- **Beweging.** Bots staan stil voor een zuiver schot, strafen op korte afstand, hurken tijdens het sproeien, herladen achter dekking en houden afstand van teamgenoten.
- **Teamwerk.** Bots delen wat ze zien, sturen steun naar een teamgenoot onder vuur, nemen wraak voor een gevallen teamgenoot en bewegen in paren in Team Deathmatch en Elimination.
- **Discipline.** Een bot houdt zijn vuur in als er een teamgenoot in de schootslijn staat.

## Gemeten, niet gegokt

Elke wijziging aan de bots wordt op dezelfde manier getest. We spelen potjes met alleen bots op alle zes maps, in elke modus, één keer met de huidige release en één keer met de nieuwe versie, en vergelijken de uitkomsten: kills, trefzekerheid, geplante bommen, veroverde vlaggen, gespeelde rondes en hoe vaak een bot vastloopt.

Dat proces ving een probleem dat we met een paar rondjes spelen nooit hadden gezien. In de eerste testronde waren de nieuwe bots zoveel beter in spotten en schieten dat vlagdragers nauwelijks overleefden. Het aantal veroverde vlaggen in de testpotjes zakte van acht naar één. Betere individuele bots hadden Flag Capture slechter gemaakt.

> De oplossing: het nieuwe gevechtsgedrag blijft voor bots die jagen en verdedigen, en bots die met het doel bezig zijn bewegen zoals voorheen. Het aantal veroveringen kwam terug op het niveau van de huidige release, binnen de normale spreiding tussen runs.

Vijf testrondes en tientallen potjes later zien de cijfers er zo uit: geen crashes, twee keer zoveel kills in Elimination, merkbaar scherper richten in Team Deathmatch, en bom- en vlagspel op hetzelfde niveau als voorheen.

## Wat er komt

Bots zijn een lang project. De routes van vlagdragers op Village en Railhouse kunnen nog slimmer, en elke nieuwe modus of map krijgt een eigen testronde. Speel je tegen ze op de officiële unranked server en ziet iets er vreemd uit, laat het ons weten op Discord. Een duidelijke beschrijving van de map en het moment helpt meer dan je denkt.
