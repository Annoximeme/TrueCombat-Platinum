---
title: Tien stukken werk, één update
date: 2026-11-08
summary: De volgende update is tegelijk door tien losse inspanningen gebouwd. Hoe die samen één build werden zonder elkaar in de weg te zitten, en hoe de laatste testpoort eruitzag.
image: img/media-village-yard.webp
tag: Testen
version: 0.34.0
updated: 2026-11-09
---
De update die nu in test is, is de breedste die Platinum tot nu toe heeft gehad. Een vernieuwde launcher, een aangepaste grafische preset, een nieuwe Graphics-pagina in het spel, wapen- en kijkbeweging, spraakcommando's, camouflage, klimgeluiden, ondersteuning voor ultrawide, Discord Rich Presence, een reeks verbeteringen met stemmingen, radio, demo's en loadout-presets, en serverwerk voor teambalans, AFK-afhandeling en meldingen. Elk daarvan komt uit een eigen lijn van werk, ontwikkeld en getest op een eigen kopie van het spel.

Dit artikel gaat over het minder zichtbare deel: hoe tien losse stukken één build worden die we op de downloadknop durven te zetten.

## Waarom eerst apart

Aan alles tegelijk werken in één gedeelde codebasis klinkt eenvoudiger, maar dan kan elke halfafgemaakte wijziging elke andere test breken. In plaats daarvan wordt elk stuk ontwikkeld tegen de huidige release, in dit geval 0.33.0, en daar getest tot het zijn eigen controles doorstaat. Pas dan wordt het overgedragen als patch: een precieze beschrijving van elke gewijzigde regel, plus een controlesom, een lijst van wat het raakt en de tests die het heeft doorstaan.

Bij die overdracht worden overlappingen zichtbaar. Drie van de tien stukken wijzigen hetzelfde bestand dat op de server een wedstrijd draait. Vier wijzigen het bestand dat jouw beeld tekent. Twee wijzigen de menu's in het spel. Geen van alle wist van de andere af terwijl ze geschreven werden.

## Samenvoegen in vaste volgorde

De patches worden in een vaste volgorde toegepast, de grootste en meest ingrijpende eerst, en elke stap wordt gecontroleerd voordat de volgende begint. Wanneer twee stukken dezelfde regels wijzigen, wordt het samenvoegen met de hand gedaan, regel voor regel, en vastgelegd. Dat gebeurde deze keer acht keer. Het meest delicate geval was de hand in eerste persoon: het camouflagewerk geeft die een nieuwe mouw, en het animatiewerk beweegt hem mee met het wapen. De oplossing was beide toe te passen, in de juiste volgorde, en te bevestigen dat het resultaat zonder één waarschuwing compileert en nog steeds de bewegings-, gevechts-, voorspellings- en entiteitstests doorstaat die elke build draait.

De menu's in het spel waren een apart geval. Twee stukken bouwen het menupakket opnieuw, één voor de nieuwe Graphics-pagina en één voor het nieuwe lettertype, en de valsspeeldetectie op servers controleert dat pakket op controlesom. Dus worden eerst de menubronnen van beide samengevoegd, wordt het pakket één keer uit dat resultaat gegenereerd, en wordt de controlesom daarvan berekend. Het pakket van een van beide stukken overnemen had een client opgeleverd die elke officiële server markeert.

> Niets in deze update wijzigt het netwerkprotocol. Een 0.33-client kan een 0.34-server nog steeds zien en erop meespelen. De upgrade hoeft alleen geïnstalleerd te worden om de nieuwe functies te krijgen.

## Wat het niet heeft gehaald

Easy Anti-Cheat stond gepland voor deze update. De code bouwt en de meeste controles slagen, maar de controle die ertoe doet, een echte client die via de echte anti-cheatbootstrapper als beschermd wordt gemeld, is niet op tijd bevestigd. Die wordt vastgehouden tot de volgende update in plaats van op gedeeltelijk bewijs uitgebracht. Dezelfde regel gold ongeveer een uur lang voor Discord Rich Presence: de eerste volledige test faalde bij de stap Discord Join, er is een fix gemaakt en opnieuw getest op beide renderers, en pas toen ging het er weer in.

## De poort

Zodra alles is samengevoegd, wordt de echte kandidaatbuild als geheel getest: zeventien geautomatiseerde wedstrijdscenario's op DirectX 12 en OpenGL, met bots, op de officiële maps, met gevechten, doelen, teamspel, instellingswijzigingen en herstarts, plus de eigen installatie- en updatetests van de launcher en de controles van de grafische presets. Een release gaat pas uit als die run groen is. Faalt één scenario, dan wordt dat onderzocht, niet opnieuw gedraaid tot het slaagt.

Eén scenario hield ons vandaag bezig. Een controle op bewegingssnelheid vergelijkt twee snelheidsinstellingen en verwacht een verhouding van minstens 1,2. Drie afzonderlijke testruns maten 1,19. Geen van de wijzigingen in die runs raakte de beweging, en dezelfde controle heeft eerder geflikkerd, dus wordt de drempel herzien en niet het spel. Het is een herinnering dat ook de testomgeving onderhoud nodig heeft.

**Update, 9 november.** De oorzaak bleek in de test te zitten, niet in het spel. De controle startte de stopwatch zodra het commando om te bewegen werd gestuurd, niet op het moment dat de speler echt in beweging kwam. Bij een trage start telde ze tot een seconde stilstaan mee, en dat trok het gemiddelde omlaag. De metingen van de server zelf lieten het volledige snelheidsverschil steeds zien. De controle meet nu vanaf het eerste moment dat de speler beweegt. Opnieuw berekend met die correctie komen alle eerdere runs uit tussen 1,48 en 1,54, de drempel bleef staan, en de volledige run van zeventien scenario's slaagde voordat 0.34.0 werd uitgebracht.

Speel je de update en voelt er iets verkeerd, zeg het ons dan op Discord met de map en het moment. Elk stuk van deze update begon als precies zo'n bericht.
