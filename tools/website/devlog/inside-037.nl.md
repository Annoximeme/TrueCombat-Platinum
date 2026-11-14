---
title: Inside 0.37.0, onze grootste update tot nu toe
date: 2026-11-14
time: 09:00
summary: Een volledig vernieuwde interface, een tactische kaart, fotomodus, optionele spelersaccounts, bots die je vuurlijn respecteren, Bomb-rondes met één leven en een lange lijst fixes uit jullie meldingen. Dit is wat er veranderd is, waarom, en hoe we het getest hebben.
image: img/devlog/a-new-look.webp
tag: Release
version: 0.37.0
---
Versie 0.37.0 is uit, een dag na de 0.36.1-hotfix. Het is de grootste update die TrueCombat: Platinum tot nu toe gehad heeft. Zes afzonderlijke stukken werk, elk apart gebouwd en getest, komen samen in één release: een nieuwe interface, een reeks visuele en gebruiksvriendelijke functies, optionele spelersaccounts, een vernieuwde studio-intro, slimmere bots en een flinke lading fixes uit jullie playtestmeldingen.

Zoveel in één update stoppen is een risico, dus zo hebben we het ook behandeld. Elk onderdeel kwam met zijn eigen tests. Ze zijn één voor één samengevoegd, telkens zo dat ze er netjes weer uit konden, en daarna is het hele spel opnieuw als één build getest voordat het in de buurt van de launcher mocht komen.

> De launcher pakt 0.37.0 vanzelf op en je instellingen blijven behouden. Deze eerste update vanaf 0.36 is eenmalig een grotere download, omdat we de manier waarop spelbestanden worden opgeslagen hebben aangepast. Daardoor kunnen toekomstige updates kleiner worden.

## Een nieuwe interface

Elk menu en de HUD in het spel zijn opnieuw opgebouwd in de nieuwe Platinum-stijl. Het doel was niet versiering. Het ging erom dat je de informatie die je nodig hebt in één oogopslag kunt lezen: duidelijkere letters, consequente witruimte en knoppen die zich op elke pagina hetzelfde gedragen.

Niet iedereen houdt van verandering, en de oude HUD hoort al lang bij TrueCombat. Daarom is de klassieke HUD er nog steeds, één schakelaar verderop in de opties. Je kunt de menu's ook schalen naar 100, 90 of 80 procent via **Opties > HUD & Effecten > Menugrootte**, en de HUD houdt nu zijn indeling op schermen die smaller zijn dan 16:9.

We hebben de nieuwe menu's getest op acht resoluties, van 1280x720 tot 3840x2160 en van 4:3 tot ultrawide, in beide renderers, en gecontroleerd dat de toetsenbordfocus bij elke menugrootte op de juiste knop belandt.

## Meer van het gevecht zien

Over deze functies schreven we uitgebreid in [Een nieuwe look, van laadscherm tot killfeed](devlog-a-new-look.html). De korte versie:

- Elke kaart heeft een eigen **laadscherm**.
- Houd **M** ingedrukt voor een **tactische kaart** van het slagveld en je squad.
- Een **podium** aan het einde van elke match zet de beste spelers in de schijnwerpers.
- **Fotomodus** en camerapaden voor screenshots en video's.
- **HDR10-uitvoer** voor HDR-schermen, en optionele kleurcorrectie per kaart.
- Het Grafisch-menu toont per instelling een geschatte GPU-belasting en een voorbeeld.
- De icoontjes in de killfeed worden getekend uit de echte wapenmodellen.
- Meldingen tonen je eigen toetsen, en foutschermen leggen uit wat er misging.

## Optionele spelersaccounts

Je hebt nog steeds geen account nodig om te spelen. Je identiteit in TrueCombat komt van een sleutel op je eigen pc, precies zoals voorheen. Nieuw in 0.37.0 is de mogelijkheid om die pc aan een account te koppelen, of dat in een paar seconden met je telefoon te doen. Met een account kun je in de launcher wisselen tussen profielen, je naam reserveren en een vinkje voor een schoon dossier op je profiel tonen. Daarnaast staat er een nieuwe optie "Op zoek naar een squad" op de Servers-pagina.

## Gameplay en fixes

De meeste fixes in deze update komen rechtstreeks uit jullie playtestmeldingen na 0.36.0. 0.36.1 bracht al de dringendste fixes voor beweging en besturing. 0.37.0 bevat die ook en voegt toe:

- **Bomb is nu één leven per ronde.** Wie halverwege een ronde binnenkomt, wacht op de volgende. In onze botmatches ging het aantal respawns in een Bomb-ronde daarmee van 26 naar nul.
- Bloedeffecten zijn terug.
- Ontbrekende texturen op de handen en de tang bij het ontmantelen zijn opgelost.
- Het vizier van de SIG 552 en de SPAS-12 staat nu correct uitgelijnd.
- Het jachtgeweer pompt na elk schot.
- Richten via het vizier heeft nu een subtiele wapenzwaai die toeneemt als je beweegt en na het sprinten. Jullie vroegen erom, en het is instelbaar.
- Benen schieten niet meer in de verkeerde animatie als je op een helling loopt.
- Kogels die ramen raken, laten nu glasinslagen zien.
- Elke optie in de instellingenmenu's is gecontroleerd op wat ze belooft: dat ze echt verandert, toegepast wordt en bewaard blijft. Een aantal opties die dat niet deden, doen het nu wel.

## Bots

Twee botwijzigingen in deze release. Bots stappen uit je vuurlijn zodra je richt of schiet, en kiezen de open kant als er een muur in de weg staat. En bots blijven bij het doel in Bomb en CTF, in plaats van achter elk geluid aan te gaan.

We hebben de botwijzigingen getest in vergelijkende matches tegen 0.36.0 op alle zes Bomb-kaarten, met dezelfde willekeurige seeds aan beide kanten, om zeker te zijn dat er verder niets veranderde. Plants, vastlopers, crashes en vastzittende bots kwamen er allemaal hetzelfde uit.

## Servers en stemmen

Bij een stemming over de kaart worden nu alleen kaarten uit de eigen rotatie van de server aangeboden, en een stemming breekt de modusrotatie van een server niet meer. Het aantal stemmingen dat elke speler mag starten, blijft nu ook bewaard na een herstart van de kaart.

Daarnaast hebben we onze beveiligingsmaatregelen aangescherpt en uitgebreid.

## De launcher

Launcher 2.4 voegt een paneel in het systeemvak en volledige bediening met een controller toe. Nieuwe installaties starten nu op de grafische preset die bij je videokaart past, ook als je de welkomstpagina overslaat. Het belangrijkste voor de toekomst: updates kunnen nu losse bestanden downloaden in plaats van één groot pakket, zodat ze kleiner zijn en beter herstellen bij een slechte verbinding.

## Hoe we het getest hebben

Voordat 0.37.0 werd verpakt, ging de definitieve build door dezelfde releasetests als elke versie ervoor, plus tests die voor elk nieuw onderdeel geschreven zijn:

- de volledige regressietests, voor beweging, gevechten, netwerkgevoel, graphics, instellingen en herstarts;
- treffers onder gesimuleerde vertraging;
- 128 updates per seconde;
- voicechat in teams en in de oefenmodus;
- de nieuwe menu's en hun opties, in beide renderers;
- het accountproces;
- het updatepad van de launcher, inclusief wat er gebeurt als een bestand niet gedownload kan worden.

Een paar dingen kan alleen een mens controleren: de HDR-uitvoer, de bediening met een controller en een handvol schermen voor toetstoewijzing. Die zijn met de hand nagekeken.

## Wat het niet gehaald heeft

Er ligt een fix klaar voor geluid dat wegvalt en een muis die loskomt in randloos venstermodus, maar we konden het oorspronkelijke probleem niet betrouwbaar genoeg nabootsen om te bewijzen dat de fix werkt. Liever dan een gok te verschepen, schuift die door naar 0.37.1. Dat geldt ook voor een nieuwe animatie bij het wisselen van wapen, een nieuwe granaatexplosie en meer personagekeuzes per klasse. Die zijn gebouwd, maar nog niet in het spel getest.

Zoals altijd: als iets niet goed voelt, druk dan op **F12** in het spel om ons een melding te sturen. Bedankt voor het spelen, en voor het vertellen wat we moeten repareren.
