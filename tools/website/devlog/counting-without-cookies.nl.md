---
title: Nieuwe spelers vinden zonder iemand te volgen
date: 2026-11-12
time: 18:00
summary: TrueCombat: Platinum gaat binnenkort op meer platformen dan ooit naar buiten. Om te weten welke daarvan echt spelers opleveren, telt de site nu bezoeken en downloads zoals hij devloglezers telt: zonder cookies, zonder externe bedrijven en zonder iets dat naar jou terugleidt.
image: img/map-stadtrand.webp
tag: Community
---
Met 0.36.0 vertellen we een veel groter publiek over TrueCombat: Platinum. ModDB, itch.io, Reddit, makers van video's, de oude TC:E-community. Sommige van die plekken zullen spelers opleveren. Andere niet. Met een klein team en beperkte tijd moeten we weten welke welke is, zodat de moeite gaat naar wat werkt.

Eerder deze maand legden we uit hoe de devlog [lezers telt zonder iemand te volgen](devlog-reads-and-ratings.html). De site gebruikt nu dezelfde aanpak voor de hele website.

## Wat er verandert

Elke pagina meldt nu één keer aan onze eigen server dat iemand hem opende: de pagina, de naam van de site die ernaar linkte, de campagnetag in de link als die er is, de taal van de pagina, en of het scherm de grootte van een telefoon, tablet of desktop heeft. Een klik op een downloadknop meldt dat er een download is gestart.

Links die we op andere platformen plaatsen gaan nu via korte adressen zoals `truecombat.eu/go/moddb`. Ze openen de gewone pagina met een kleine campagnetag, die de site één keer leest en daarna uit de adresbalk haalt, zodat een link die je kopieert en deelt schoon blijft.

## Wat er niet verandert

- Geen cookies. Er wordt niets in je browser opgeslagen om te tellen.
- Geen Google Analytics, geen Meta-pixel, geen enkel analysebedrijf.
- Geen IP-adressen bewaard. De server gebruikt je verbinding één moment om je één keer per dag te tellen, en om middernacht wordt het dagelijkse geheim achter die telling gewist, samen met alles wat ermee gemaakt is.
- Global Privacy Control en Do Not Track worden gerespecteerd. Staat een van beide aan, dan word je helemaal niet geteld.

Wat overblijft is een reeks dagtotalen: zoveel mensen openden de mapspagina, zoveel kwamen van ModDB, zoveel van hen downloadden de game. Genoeg om goede beslissingen te nemen, en niet genoeg om iets over één van jullie te zeggen.

## Waar je de details leest

Alles wat we tellen, op de website en in de game, staat nu op één plek: de nieuwe [privacypagina](privacy.html), in alle vijf talen van de site. Als we ooit iets nieuws gaan tellen, verandert eerst die pagina en meldt de devlog het.

## Wat er hierna komt

De launcher krijgt een optionele schakelaar om anonieme prestatie- en crashgegevens te delen, zodat we zien welke grafische kaarten en drivers aandacht nodig hebben voordat een playtest het ons vertelt. Hij staat uit tenzij je hem aanzet, en staat gepland voor de update na 0.36.0. We publiceren de volledige lijst van wat hij verstuurt voordat hij verschijnt.

De code die het tellen doet staat in de openbare repository, naast de statistiekendienst. Zoals altijd hoef je ons nooit op ons woord te geloven.
