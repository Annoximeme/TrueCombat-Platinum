---
title: Elk schot laat een spoor na
date: 2026-11-08
summary: Kogelgaten, inslaggeluiden, het knallen van een rakelingse kogel en de originele wapenanimaties. Zo brengt de volgende update het gevoel van een TC:E-vuurgevecht terug.
image: img/devlog/impacts-warehouse.webp
tag: Gameplay
version: 0.33.0
---
Vraag een TC:E-veteraan hoe een vuurgevecht aanvoelde en je hoort zelden iets over schadegetallen. Je hoort over pleisterwerk dat naast je hoofd van de muur spat, het knallen van een kogel die je net miste, en de slede die op het slechtst denkbare moment openblijft op een leeg pistool. De getallen klopten in Platinum al. De volgende update gaat over alles daaromheen.

## Vuur dat sporen nalaat

Elk oppervlak krijgt nu de originele kogelgaten voor zijn materiaal, waar de kogel erin gaat en waar hij eruit komt. Elke treffer geeft stof, splinters, vonken of bloed, afhankelijk van wat hij raakt, en speelt het originele inslaggeluid voor dat oppervlak.

![Een vers kogelgat in een stapel kratten in een magazijn, in DirectX 12](img/devlog/impacts-warehouse.webp "Eén kogel door een stapel kratten. Het gat, het stof en het geluid komen allemaal uit de originele materiaalset.")

Ook de rakelingse kogel is terug. Een kogel die vlak langs je hoofd gaat, maakt de korte, scherpe knal waar TC:E-spelers op leerden te reageren lang voordat ze de schutter zagen. Hij vertelt je dat je gezien bent, en ongeveer van waar.

Inslagen zijn alleen beeld en geluid. Ze veranderen niets aan schade, doorboring of waar een kogel doorheen kan. Dat blijft precies zoals in de huidige versie.

## Het wapen in beeld, opnieuw opgebouwd

We vergeleken elke speler- en wapenanimatie in Platinum met het originele spel, een voor een, en schreven we elk verschil op. De animaties in eerste persoon zijn nu opnieuw opgebouwd vanuit die lijst.

- Pistolen blijven met de slede open staan na het laatste schot.
- Akimbo-pistolen vuren afwisselend met de linker- en rechterhand.
- Herladen maakt verschil tussen een half en een leeg magazijn, zoals in TC:E.
- Shotguns laden patroon voor patroon.
- Bij het wisselen van wapen gaat het oude eerst omlaag voordat het nieuwe omhoogkomt.

Elk wapen krijgt ook een nieuwe mondingsflits in eerste persoon, en sluipschuttersgeweren tonen het vizier als je richt.

## Randen, niet alleen ladders

Klimmen op randen is terug. Spring tegen een rand die binnen bereik is en je trekt jezelf erop, zoals in het origineel. Dat opent dezelfde kortere routes en klimplekken die veteranen kennen, en niets meer.

![Een soldaat die zich omhoogtrekt op een krat in het magazijn van Railhouse](img/devlog/ledge-railhouse.webp "Klimmen op een stapel kratten in Railhouse. De automatische test doet dezelfde klim op DirectX 12 en OpenGL.")

## Hoe we het testten

Elk onderdeel heeft een eigen automatische test die draait op DirectX 12 en op OpenGL. De inslagtest schiet op muren en op een bot, en controleert dat de server en het spel het eens zijn over elke treffer en het oppervlak, en dat een kogel die vlak langs een speler gaat als rakelings telt. De klimtest zoekt echte randen in de map en klimt erop. Alles draait opnieuw in de volledige regressietest voordat de update verschijnt.

## Wat nog komt

Mondingsflitsen en explosies werpen nog geen schaduw. Daar werken we hierna aan, en het komt in een latere update zodra het aan dezelfde lat voldoet: trouw aan het origineel, en snel genoeg dat niemand het hoeft uit te zetten.
