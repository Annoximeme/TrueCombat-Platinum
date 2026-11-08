---
title: Als de test het mis heeft
date: 2026-11-08
summary: Onze terugslagcontroles keurden de Desert Eagle af. Het spel had gelijk. Zo kwamen we erachter, en daarom jagen we liever op een vals alarm dan dat we een echt probleem missen.
image: img/media-soldier-hd.webp
tag: Testen
---
Platinum is een herbouw van TrueCombat: Elite, dus "het voelt ongeveer goed" is nooit genoeg. Elk wapen wordt vergeleken met het originele spel: schade, vuursnelheid, spreiding, en hoe het beeld omhoog schiet en terugkomt als je vuurt. Die controles draaien automatisch, op DirectX 12 en op OpenGL, voor elke release.

## Het rode lampje

Tijdens routinetests voor de volgende update faalde de terugslagcontrole op één wapen. Vanuit de heup afgevuurd kwam de Desert Eagle niet terug waar de controle dat verwachtte. Na elk schot eindigde het beeld net iets hoger dan het zou moeten, en over een volledig magazijn liep dat op tot een duidelijk verschil.

Zo'n uitslag wordt nooit genegeerd. Terugslag bepaalt mede wat elk wapen is, en de Desert Eagle is een wapen waar mensen sterke herinneringen aan hebben.

## Terug naar het origineel

We gingen dus terug naar het originele spel en volgden precies wat er gebeurt als een schot wordt gelost. Elk schot heeft een trap: hoe ver het beeld omhoog wordt geduwd. Het originele spel verplaatst je beeld met de volle trap, maar begrenst hoeveel daarvan het later weer omlaag trekt.

Voor de meeste wapens doet die grens er nooit toe, omdat hun trap kleiner is dan de grens. De Desert Eagle vanuit de heup is de uitzondering. Zijn trap is groter dan de grens, dus elk schot laat een kleine, blijvende klim achter die het herstel nooit terugneemt. Zo gedraagt het origineel zich, en het is een deel van waarom een Deagle vanuit de heup voelt zoals hij voelt.

Platinum deed al precies hetzelfde. De controle niet: die ging ervan uit dat de volle trap werd hersteld.

## Het juiste repareren

We hebben de controle aangepast, niet het spel. Met de grens erbij slaagt de Desert Eagle op DirectX 12, op OpenGL en tegen de huidige release.

> Hier kwam geen enkele gameplaywijziging uit. Was je bang dat de Deagle "gerepareerd" zou worden tot iets wat hij nooit was: dat gebeurt niet.

## Waarom we dit vertellen

Een artikel over een test die het mis had, lijkt misschien vreemd om te publiceren. Wij vinden dat het laat zien hoe Platinum gemaakt wordt. Elke waarde wordt vergeleken met het origineel, elk verschil wordt onderzocht voordat er iets verandert, en soms bewijst het onderzoek dat het spel gelijk had. Een vals alarm kost ons een middag. Een echt verschil dat erdoor glipt, kost elke speler die nog weet hoe het wapen hoort te voelen.
