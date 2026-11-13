---
title: Elke map in 3D, in je browser
date: 2026-11-13
time: 07:00
summary: De zes mappagina's hebben nu een 3D-model van de echte map dat je kunt draaien, openknippen en bestuderen voor je eerste ronde, en elke update krijgt een eigen pagina.
image: img/devlog/maps-in-3d.webp
tag: Community
---
Een map leren kende tot nu toe maar één weg: een paar rondes verliezen. Vanaf vandaag heeft elke mappagina een 3D-model van het volledige level, zodat je de map kunt verkennen voor je inlogt.

![Village in de 3D-mapweergave](img/devlog/maps-in-3d.webp "Village, van boven de kant van de Special Forces")

## Gebouwd uit de bestanden van het spel

De modellen zijn niet nagetekend. Ze zijn rechtstreeks omgezet uit de mapbestanden die het spel laadt, dus elke muur, trap en elk raam staat precies waar het in een potje staat. De belichting komt van het licht dat de oorspronkelijke mappers in elk level hebben ingebakken. Daarom gloeit het spoorwegemplacement op Railhouse zoals in het spel.

Gebiedsnamen, beide bomsites, de vlaggen en beide spawnzones zweven boven het model, met dezelfde namen die het spel op je HUD toont. Met een schuifregelaar voor de dakhoogte knip je de gebouwen van bovenaf open, zodat je een route door de kelder op Railhouse of de tunnel op Snow kunt volgen zonder te gokken.

## Zo gebruik je het

Open een mappagina en kies **Laad de 3D-weergave**. Sleep om de camera te draaien, sleep met rechts of houd Shift ingedrukt om te verschuiven, en scroll om te zoomen. Met het toetsenbord draaien de pijltjestoetsen, verschuiven Shift en de pijltjes, zoomen plus en min, en zet R de camera terug. Het model is een tot twee megabyte groot en wordt pas gedownload als je erom vraagt.

> De 3D-weergave heeft een browser met WebGL 2 nodig. Elke recente versie van Chrome, Edge, Firefox en Safari heeft dat. Lukt het niet, dan toont het plan op dezelfde pagina dezelfde indeling.

## Een pagina voor elke update

Ook de patch notes hebben een nieuwe plek. Elke versie krijgt nu een eigen releasepagina met de belangrijkste wijzigingen bovenaan, een korte samenvatting per onderdeel en de volledige lijst eronder, met links naar de vorige en de volgende versie. De nieuwspagina toont ze nog steeds allemaal, en elk item linkt naar zijn pagina.

## Beter leesbaar voor iedereen

We hebben de hele site ook door een toegankelijkheidscontrole gehaald. Die slaagde voor de WCAG 2.2 AA-controles zonder één overtreding, elke link en knop toont waar de toetsenbordfocus staat, en niets beweegt op het scherm als je systeem is ingesteld op minder beweging. De site volgt nu ook de modus voor hoog contrast van Windows en de instelling voor meer contrast op je toestel.
