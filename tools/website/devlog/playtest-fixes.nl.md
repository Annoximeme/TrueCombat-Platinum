---
title: Wat de playtests ons leerden
date: 2026-11-09
summary: Onze laatste communityplaytests leverden een duidelijke lijst problemen op, met de gunplay voorop. Een grote reeks fixes staat klaar voor de volgende patch. Hier staat alles wat we vonden, in welke volgorde we het oplossen en hoe het past bij de rest van het werk dat eraan komt.
image: img/media-grenade.webp
tag: Roadmap
updated: 2026-11-12
---
De beste test voor een shooter is een volle server met mensen die weten hoe het hoort te voelen. Onze recentste communityplaytests gaven ons precies dat, en het oordeel was eerlijk: de basis staat, maar te veel kleine dingen voelen nog anders dan in het origineel. In deze post staat elk probleem dat uit die sessies kwam, de volgorde waarin we ze aanpakken en waar ze staan naast het werk uit [Waar we hierna aan werken](devlog-whats-next.html).

Het resultaat is een lange lijst fixes, en die staan klaar voor de volgende patch. Een datum krijgt die pas als hij klaar is: elke fix komt uit zodra hij door de volledige testronde komt, en we werken deze post bij naarmate er punten klaar zijn. Elke update brengt Platinum een stap dichter bij het vernieuwde, betere spel dat we voor ogen hebben.

> Update, 12 november: het grootste deel van deze lijst zit in 0.35.0. Bij elk punt hieronder staat nu hoe het ervoor staat. [Achter de schermen van 0.35.0](devlog-inside-035.html) legt uit hoe de fixes tot stand kwamen en wat de update niet haalde.

> Gunplay komt eerst. Zolang niet elk schot landt waar je richt en doet wat het moet doen, is niets anders op deze lijst even belangrijk.

## Gunplay

Dit is de belangrijkste groep, en de groep waarover we het meest horen.

- **Treffers op afstand.** Schoten op grotere afstand registreren niet altijd op een doelwit dat duidelijk onder het vizier stond. We controleren elke hitbox tegenover het spelermodel op afstand, met en zonder lagcompensatie, op een echte internetverbinding. *Update, 12 november: 0.35.0 lost treffers op leunende spelers en verloren schoten vlak na een respawn op. Eén resterend geval, schoten op liggende spelers, werd na de release gevonden en wordt opgelost.*
- **Kogels die niet landen waar je richt.** Sommige wapens, waaronder de SIG, schieten net naast het punt waar het vizier staat. We stoppen niet bij de gemelde wapens: elk wapen in het arsenaal krijgt dezelfde controle, zodat de fix volledig is en niet geval per geval. *Update: de controle wapen per wapen loopt. De oorzaken die we tot nu toe vonden, zijn de fixes voor leunen en respawnen in 0.35.0.*
- **Spreiding en richten per wapen.** De spreiding van elk wapen, hoe die toeneemt tijdens het vuren en hoe het wapen zich gedraagt bij richten via het vizier, vergelijken we wapen per wapen met de originele waarden. *Update: gecontroleerd. De spreiding van elk wapen klopt met de originele waarden, en richten via het vizier vertraagt je nu zoals in het origineel.*
- **Schade.** Het schademodel voor geweren, SMG's, pistolen en sluipschuttersgeweren krijgt een volledige controle, inclusief hoe de schade afneemt met de afstand en per lichaamsdeel. *Update: gecontroleerd. De schadewaarden kloppen met de originele tabellen. Valschade treft nu de benen in plaats van het lichaam.*
- **Het ritme van de grendel.** Het sluipschuttersgeweer met grendel herlaadt te snel tussen twee schoten. Het krijgt het originele tempo terug, en dat is een groot deel van wat het geweer zo bedachtzaam doet aanvoelen. *Opgelost in 0.35.0.*
- **Granaat gooien vuurt je wapen af.** Een granaat gooien kan tegelijk je wapen afvuren. Dit is gewoon een bug en wordt in de eerste ronde opgelost. *Opgelost in 0.35.0, samen met het koken van granaten.*

Elke wapenwijziging wordt gecontroleerd met een automatische test die elk wapen op vaste doelen en afstanden afvuurt en het resultaat met het originele spel vergelijkt, zodat een fix voor het ene wapen niet ongemerkt een ander breekt.

## Maps

- **Onzichtbare muren.** Spelers vonden onzichtbare obstakels op plekken waar niets je zou mogen tegenhouden, vooral rond het kleine huis bij de bomsite op Delta. *Opgelost in 0.35.0 op elke map: het waren palen van veroveringspunten uit Flag Capture, die in de andere modi solide bleven.*
- **Textures.** Sommige oppervlakken tonen de verkeerde texture. In plaats van alleen de gemelde plekken te verbeteren, lopen we elke map oppervlak voor oppervlak door en corrigeren we alles wat niet klopt. *Update: elke map werd oppervlak per oppervlak gecontroleerd, zonder ontbrekende textures. Plaatsvervangende textures op wapenonderdelen zijn opgelost in 0.35.0.*

## Bewegen en geluid

- **Springafstand.** Sprongen komen niet zo ver als in het origineel. Beweging voelt een TC:E-speler meteen, dus dit meten we tegenover het origineel in plaats van het op gevoel af te stellen. *Opgelost in 0.35.0. Sprongen vanuit stilstand op lage objecten en het herstel na een landing kloppen nu met het origineel.*
- **Gehurkt lopen.** Gehurkt bewegen is te snel en te luid, en het beeld wiebelt te veel. Alle drie worden weer rechtgezet. *Opgelost in 0.35.0.*
- **Je eigen voetstappen.** Je eigen voetstappen ontbreken soms helemaal. We zoeken uit waarom en lossen het op. *Update: de timing van voetstappen werd in 0.35.0 opnieuw opgebouwd vanuit het origineel. Nog een oorzaak, rond de schakelaars voor sprinten en wandelen, is gevonden en wordt getest.*
- **Wapengeluiden.** Sommige wapens spelen het verkeerde geluid. Van elk wapen controleren we de vuur- en hanteergeluiden tegenover de originele set. *Update: explosies klinken in 0.35.0 niet meer gedempt door muren in de buurt. Klinkt een wapen voor jou nog verkeerd, druk dan op F12 in het spel en vertel ons welk.*
- **Geluid als toeschouwer.** Geweervuur klinkt verkeerd als je een andere speler volgt. Toekijken moet precies zo klinken als zelf spelen. *Opgelost in 0.35.0.*

## Menu's en matchverloop

- **Opties in het pauzemenu.** Het Esc-menu heeft nog geen instellingen. Je zult midden in een match je muisgevoeligheid en andere opties kunnen aanpassen, zonder het spel te verlaten. *Opgelost in 0.35.0 met de nieuwe pagina MOUSE & VIEW.*
- **Opwarmfase.** De opwarmfase voor een match is bedoeld om je loadout te kiezen en te praten met de spelers die binnenkomen. Nu werkt die niet zoals het hoort, en we werken hem opnieuw uit. *Opgelost in 0.35.0. De opwarmfase is nu een oefenronde.*
- **Instant replay.** Twee kleine fixes uit de vorige update: een clip die je tijdens de opwarmfase opslaat, kan korter uitvallen dan verwacht, en de bevestiging zegt altijd 30 seconden, wat de echte lengte ook is. *Niet in 0.35.0. Wordt aan gewerkt.*

## Bots

- **Richten via het vizier en leunen.** Bots richten nooit via het vizier en leunen nooit, waardoor ze makkelijk te lezen zijn. Ze leren allebei. *Update: sinds 0.35.0 brengen bots hun wapen zichtbaar naar de schouder als ze richten. Wanneer ze richten en leunen, hoort bij het botwerk dat loopt.*
- **Routes.** Bots nemen te vaak dezelfde routes. Ze gaan meer afwisselen, en leren later van de routes die echte spelers op elke map nemen. *Loopt, als deel van het botwerk uit [De weg vooruit, voluit](devlog-the-road-ahead.html).*

## Kleinere punten

- **Bugmeldingen in het spel.** Een `/bug`-commando en een knop "Een bug melden" in het Esc-menu. Je melding komt bij het team aan met een screenshot, je positie op de map en de technische details die nodig zijn om het probleem na te spelen. Na deze testronde is dat een tool die we zelf ook duidelijk willen. *Uitgebracht in 0.35.0: druk op F12, of op REPORT A BUG in het pauzemenu.*
- **Staffbadge.** De badge die teamleden in het spel herkenbaar maakt, krijgt een verfijnder uiterlijk. *Niet in 0.35.0.*

## Daarnaast

De playtestfixes komen eerst, maar de rest van het plan is niet verdwenen. Het meeste werk voor online spelen is gebouwd en wacht op zijn test in de echte wereld: verbindingskwaliteit op het scorebord, een pinglimiet en bescherming bij opnieuw verbinden op Ranked, met één klik meedoen vanaf de website en Discord, pick-ups op Discord, betere admintools en IPv6-ondersteuning voor spelers en servers.

Daarna volgen de grotere functies: 2D-replays van matches met automatische hoogtepunten, pings met locatie, een coach na de match, heatmaps en een publiek balansoverzicht, wekelijkse contracten en seizoenen, vrienden en samen in een party meedoen, en bots die zich aanpassen aan de spelers op de server. [Waar we hierna aan werken](devlog-whats-next.html) beschrijft ze allemaal uitgebreider. Easy Anti-Cheat wacht nog op zijn laatste controle en komt uit zodra die rond is. *Update: Easy Anti-Cheat zit in 0.35.0 en de officiële servers vereisen het nu. Het spelgedeelte van het werk aan online spelen hierboven zat in dezelfde update.*

## Bedankt

Elk punt hierboven komt van spelers die de tijd namen om te spelen, op te letten en het ons te vertellen. Dat soort testen kunnen we niet alleen, en daarom bevat de volgende patch zoveel fixes. Zie je nog iets, of is een van deze problemen voor jou belangrijker dan de rest, laat het ons weten op [Discord](https://discord.gg/8kcHdg2Hch). De [roadmap](index.html#roadmap) toont wat er klaar is naarmate we vorderen.
