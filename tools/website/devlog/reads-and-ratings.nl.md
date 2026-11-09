---
title: Lezers tellen zonder iemand te volgen
date: 2026-11-09
time: 18:00
summary: Elk devlogartikel eindigt nu met een sterrenbeoordeling, en we zien eindelijk welke artikelen gelezen worden. Zo hebben we dat gebouwd, zonder cookies, zonder analytics en zonder iets op te slaan dat naar jou terugwijst.
image: img/map-northport.webp
tag: Community
---
Deze website heeft vanaf de eerste dag één vaste regel: bezoekers worden niet gevolgd. Geen analysescripts, geen cookies, geen ingesloten inhoud van derden die laadt voordat je erop klikt. Aan die regel verandert niets.

Het betekende wel dat we de devlog blind schreven. We wisten niet welke artikelen de moeite waard waren, welke mensen halverwege opgaven en over welke onderwerpen je meer wilt lezen. Dus bouwden we het kleinste ding dat precies die vragen beantwoordt, en niets meer.

## Wat je ziet

Onderaan elk artikel staat nu één vraag: **was dit artikel de moeite waard?** Kies één tot vijf sterren. Je kunt je keuze tot het einde van de dag aanpassen, en een account heb je nooit nodig.

Zodra een artikel vijf beoordelingen heeft, verschijnt het gemiddelde naast de datum op de devlog. Onder de vijf zegt één vroege stem meer over die ene lezer dan over het artikel, dus die houden we voor onszelf tot er genoeg is om op te bouwen.

## Wat we tellen, en wat niet

Als een artikel tien seconden op je scherm open staat, stuurt je browser één bericht naar onze eigen server: *iemand heeft dit artikel gelezen*. Kom je daarna aan het einde van het artikel, dan volgt er nog één: *iemand heeft het uitgelezen*. Dat is het volledige signaal. Wie een pagina opent en meteen weer weggaat, stuurt niets.

Om een lezer één keer te tellen in plaats van bij elke herlaadbeurt, moet de server een herhaald bezoek één dag lang herkennen. Dat doet hij met een vingerafdruk in één richting, gemaakt van je verbinding en het artikel, gemengd met een willekeurig geheim dat maar één dag bestaat. Om middernacht worden het geheim en alle vingerafdrukken gewist. Daarna kan niemand nog achterhalen wie wat gelezen heeft, wijzelf ook niet.

Wat we blijvend bewaren, is een handvol getallen per artikel per dag: hoeveel mensen het lazen, hoeveel het uitlazen en hoeveel sterren het kreeg.

Wat we nooit bewaren:

- IP-adressen, browsergegevens of apparaatinformatie
- Cookies, van welke soort ook
- Iets van Google, Meta of een ander analysebedrijf
- Enig verband tussen een beoordeling en de persoon die ze gaf

> Je sterrenbeoordeling wordt alleen in je eigen browser onthouden, zodat de sterren gevuld blijven als je terugkomt. Die notitie verlaat je computer nooit.

## Waarom leesaantallen nog niet openbaar zijn

Voorlopig ziet alleen de studio de cijfers. Een gloednieuwe devlog met kleine getallen naast elk artikel vertelt een bezoeker weinig, en we tonen ze liever zodra ze iets betekenen. Als het zover is, is dat één schakelaar aan onze kant.

## Eerlijk houden

Iedereen kan beoordelen, dus dat heeft wat bescherming nodig. Elke lezer geeft één beoordeling per artikel per dag, een tweede stem vervangt de eerste, en de server remt iedereen af die veel meer verzoeken stuurt dan iemand die een pagina leest ooit zou doen. Zoekmachines worden volledig genegeerd.

Zoals altijd: heb je vragen over hoe dit werkt, stel ze ons op Discord. De code die het tellen doet, staat in de openbare repository, dus je hoeft ons nooit op ons woord te geloven.
