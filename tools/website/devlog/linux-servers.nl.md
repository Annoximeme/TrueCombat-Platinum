---
title: De officiële servers draaien nu op Linux
date: 2026-11-09
summary: Beide officiële servers zijn overgestapt op een native Linux-versie van de 0.34.0-server. Wat dat betekent voor je matches, waarom we het deden en hoe we ervoor zorgden dat we het binnen enkele seconden konden terugdraaien.
image: img/shot-hosted.webp
tag: Servers
version: 0.34.0
---
Tot deze week draaiden de officiële servers de Windows-versie van de gameserver op een Linux-machine, via een compatibiliteitslaag die elke Windows-aanroep ter plekke vertaalt. Dat werkte, en het heeft ons door elke update tot nu toe gedragen. Maar het was nooit het plan voor de lange termijn. Sinds de vroege uren van 9 november draaien zowel Official #1 Ranked als Official #2 Unranked een native Linux-versie van de 0.34.0-server.

## Wat je merkt

Als het goed is: niets. De maps, regels, rotatie, rangen en matchgeschiedenis staan precies waar ze stonden. Je rating is onaangeroerd meegekomen, want de servers hielden hun instellingen en statistiekmappen en alleen het programma dat ze draait werd vervangen. De 0.34.0-client en de 0.33-client komen er allebei gewoon op.

Wat verandert, zit eronder. Een native server betaalt niet meer elke frame voor vertaling, dus hij gebruikt minder van de machine en heeft meer ruimte als een match druk wordt. In tests gebruikte een volle match met tien bots, op twee keer de huidige tickrate, ongeveer zeven procent van één processorkern.

## Waarom het ertoe doet

Die ruimte is wat ons later de tickrate laat verhogen. De servers sturen nu twintig keer per seconde een update. Veertig zou beweging en treffers strakker laten aanvoelen, vooral in gevechten van dichtbij, maar alleen als de server het ruim bijhoudt en de hitregistratie nog steeds klopt met wat jij op je scherm zag. De snelheid verdubbelen is niet iets wat we aanzetten in de hoop dat het goed gaat.

> De tickrate op de officiële servers is nog niet veranderd. Die gaat pas omhoog als een aparte hitregistratietest over het internet laat zien dat het beter is, niet alleen sneller.

De Linux-versie is ook de versie die communityhosts krijgen. Sinds 0.34.0 bevat elke release naast de Windows-download een kant-en-klaar Linux-serverpakket, gebouwd uit dezelfde broncode als de officiële servers. Huur je ergens een kleine server, dan kun je nu precies draaien wat wij draaien.

## Hoe de overstap ging

De overstap gebeurde laat in de nacht, in een rustig moment, één server tegelijk. Voordat er iets werd aangeraakt, werd de Linux-versie vergeleken met de release: dezelfde gamebestanden, dezelfde checksums, dezelfde maps. De oude opstelling bleef naast de nieuwe staan. Teruggaan is één aanpassing en een herstart, wat seconden duurt, en dat pad lag klaar voordat de eerste server werd omgezet.

De waakhond uit [Wat de officiële servers draaiende houdt](devlog-official-servers.html) hield beide servers de hele tijd in de gaten, zoals hij elke minuut van elke dag doet.

## Wat hierna komt

Twee dingen volgen direct uit deze overstap. Eerst de hitregistratietest over een echte internetverbinding, op beide tickrates en met bewust toegevoegde vertraging, zodat we zien hoe het spel zich gedraagt voor spelers die verder weg zitten. Daarna automatische serverupdates: nieuwe releases verschijnen al met het Linux-pakket, en de officiële servers pakken ze zelf op zodra het updatescript is aangepast aan hun opstelling.

Voelt een match op een officiële server anders sinds de overstap, in goede of in slechte zin, laat het ons dan weten op Discord met de server, de map en het tijdstip. Precies die feedback heeft deze verandering nodig.
