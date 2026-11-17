---
title: Inside 0.37.2, ogen open
date: 2026-11-16
time: 03:30
summary: Een live minimap, treffers die je voelt, friendly fire, en een spel dat van de taakbalk tot het eerste beeld als Platinum oogt. Dit is wat er in 0.37.2 veranderd is, en waarom.
image: img/hero-snow-warehouse.webp
tag: Release
version: 0.37.2
kicker: Update 0.37.2
---
0.37.1 ging over het rechtzetten van wat volgens jullie niet goed voelde. 0.37.2 gaat over overzicht: weten waar je team is, weten wanneer er op je geschoten wordt, en weten dat elke kogel die je afvuurt telt, ook die ene die een teamgenoot raakt.

> De launcher installeert 0.37.2 vanzelf en je instellingen blijven behouden.

## Een live minimap

De tactische kaart was altijd maar één toets ver weg, maar een toets ingedrukt houden om te zien waar je team is, betekent je handen uit het gevecht halen. 0.37.2 voegt een **live minimap** toe in de rechterbovenhoek.

Hij draait mee met je blik, zodat boven altijd de richting is waarin je kijkt. Je ziet de indeling van de kaart, de bomlocaties, het noorden en je eigen team. Vijanden verschijnen er nooit op: de minimap toont alleen wat jouw kant al weet. Het doelpaneel en de netwerkweergave schuiven omlaag om plaats te maken, en gaan terug naar hun gewone plek als je de minimap uitzet onder **Opties > HUD & effecten**.

**M** opent weer de volledige tactische kaart. Oudere profielen hadden die toets na een eerdere wijziging aan iets anders gekoppeld, en worden automatisch rechtgezet. Had je bewust een andere actie op M gezet, dan blijft die waar je hem zette. Servers die de tactische kaart uitzetten, verbergen ook de minimap.

## Treffers die je voelt

Tot nu toe was je gezondheidsbalk vaak het eerste teken dat er op je geschoten werd. Dat is te laat. In 0.37.2 schokt je beeld bij een treffer, kleurt het scherm kort rood en verschijnt er een bloedvlek aan de kant waar het schot vandaan kwam, zodat je weet waar je je naartoe moet draaien voordat je ook maar één getal gelezen hebt.

Onder vuur liggen telt ook. Kogels die langs je heen fluiten, halen de kleur uit de randen van je scherm en laten je beeld trillen. Iemand vastpinnen is weer een echte tactiek, en je merkt het als het jou overkomt.

Beide effecten werken met de Platinum- en de Classic-HUD, in DirectX 12 en OpenGL.

## Friendly fire staat aan

Samenspelen betekent je teamgenoten vertrouwen met je rug, en dat vertrouwen betekent pas iets als een slordig schot een prijs heeft. **Friendly fire staat nu aan.** Kogels, messen en granaten verwonden teamgenoten. Teamkills tellen als teamkills en leveren geen punten meer op.

Kijk goed waar je op schiet, en denk twee keer na voor je een granaat gooit in een kamer die je team aan het uitkammen is.

## Een HUD die uit de weg blijft

Wanneer de Platinum-HUD zijn killkaart toont, is de regel "You were killed by" midden in beeld verdwenen. Die zei twee keer hetzelfde, precies op de plek waar je keek. De Classic-HUD houdt de oorspronkelijke regel.

Gekleurde spelersnamen tonen nu elke kleur op de Platinum-HUD. Een aantal kleuren uit de naamkleurkiezer van de launcher verscheen voorheen zonder kleur in de chat, in het Deployment-menu en op HUD-kaarten. Ze verschijnen nu zoals je ze gekozen hebt.

## Granaten echt gooien

Granaten spelen nu hun animaties voor het trekken van de pin en het gooien in eerste persoon, en vertrekken uit je werphand in plaats van uit het midden van het scherm. Waar een granaat landt, is niet veranderd: de worp is precies even sterk en even nauwkeurig als voorheen. Hij ziet er nu alleen uit als een worp.

## Namen

Is een naam gereserveerd door de eigenaar en komt iemand anders ermee binnen, dan speelt die als "Player####". Tot nu toe werd nooit uitgelegd waarom. Het spel zegt het nu één keer, in gewone woorden. Namen die stafftags nabootsen, worden ook grondiger opgeschoond.

## Een spel dat als Platinum oogt

Tot nu toe toonden het spelvenster, de taakbalk en Taakbeheer nog het icoon en de naam van de oude engine. Ze tonen nu het Platinum-embleem en **TrueCombat: Platinum**.

De intro van Team Terminus en Platinum had een eigen probleem: als je in de launcher op Spelen, Meedoen of Oefenen drukte, sprong het spel meteen naar het laden, en zag je de intro alleen als het spel naar het hoofdmenu opende. De intro speelt nu eerst, en het spel start zodra hij afgelopen is. Launcher 2.5.1 brengt die wijziging.

## Achter de schermen

Bots zijn sneller klaar wanneer een server op dezelfde kaart tussen spelmodi wisselt. Windows-servers zijn lichter en draaien soepeler. De What's New-kaart in het spel is bijgewerkt voor deze versie.

## Hoe we het getest hebben

0.37.2 ging door de volledige releasetest: beweging, gevechten, netwerkgevoel, graphics, instellingen en herstarts, in DirectX 12 en OpenGL, plus de launcher, de installer en het updatepad. Elke nieuwe functie in deze update werd ook apart getest, op beide renderers en met beide HUD-stijlen, voordat hij in de release ging.

## Nog op ons lijstje

Twee dingen zijn nog niet af. De killfeed en het scorebord tonen nog teamkleuren in plaats van de eigen naamkleur van elke speler. En sommige spelers verliezen nog steeds al het geluid na alt-tabben of na een wijziging aan hun audioapparaat. Aan beide wordt gewerkt voor een volgende update. Tot de geluidsfix er is, brengt een herstart van het spel het geluid terug.

Zoals altijd: voelt er iets niet goed, druk dan in het spel op **F12** om ons een melding te sturen. Bedankt om te spelen.
