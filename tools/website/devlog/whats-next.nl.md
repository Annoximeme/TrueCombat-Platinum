---
title: Waar we hierna aan werken
date: 2026-11-09
summary: Nu 0.34.0 uit is, een open blik op het werk dat erachter klaarstaat: beter online spelen, pick-ups via Discord, met één klik meedoen en een reeks nieuwe functies op basis van een gedeeld matchverslag. Plannen, geen beloftes.
image: img/media-map-vote.webp
tag: Roadmap
---
0.34.0 is uit en de officiële servers zijn overgestapt op Linux. Een goed moment om te laten zien wat er komt. Alles hieronder is gebouwd en wacht op testen, of gepland en nog niet begonnen. We zeggen telkens wat wat is, en niets ervan heeft een datum. Een functie komt uit als ze door de volledige testronde komt, niet als de kalender dat zegt.

## Online spelen

Dit werk is het verst. Het meeste is al gebouwd en los getest, en moet nu naar de 0.34.0-code en getest worden met echte spelers op echte verbindingen.

- **Verbindingskwaliteit die je kunt zien.** De server meet pakketverlies, jitter en ping voor elke speler en deelt dat, zodat het scorebord een verbindingsicoon naast elke naam kan tonen en je in het spel een netwerkgrafiek kunt openen. Voelt iets niet goed, dan zie je of het aan jouw verbinding ligt, aan die van een ander of aan de server.
- **Eerlijkere ranked matches.** Een pinglimiet op Official #1 Ranked, zodat één heel verre verbinding de match niet voor iedereen verpest. Val je weg en kom je binnen een paar minuten terug, dan houd je je team en je score. Wie een teammatch die hij aan het verliezen is bewust verlaat, krijgt het volledige ratingverlies, en verlaten matches staan op je profiel.
- **Met één klik meedoen.** Links die de launcher openen en je meteen op een server zetten, vanaf de website of vanuit Discord. Is de server vol, dan wacht de launcher op een vrije plek en komt hij er vanzelf op. Een korte verbindingscheck voor je meedoet waarschuwt voor een lange route en zet extra pakketbescherming aan bij verbindingen die pakketten verliezen.
- **Pick-ups op Discord.** Een `/pickup`-wachtrij met een ready-check, teams die op niveau worden verdeeld en een server die voor je wordt vastgelegd, met een joinlink voor elke speler.
- **Betere tools voor admins.** Tijdelijke bans, een banlijst die over alle officiële servers wordt gedeeld en spelersmeldingen die direct naar het juiste moment in de opname van de server linken. Statistieken die niet lijken te kloppen, worden gemarkeerd zodat staff ze kan bekijken. Een mens neemt altijd de beslissing, nooit het systeem.
- **Communityservers.** Een kant-en-klare containeropstelling om je eigen server te hosten, IPv6-ondersteuning voor spelers en servers, en een Verified-label voor communityservers die de officiële versie draaien.

> Snellere servers komen bewust als laatste. De tickrate gaat pas omhoog als een hitregistratietest over het internet laat zien dat treffers beter registreren, niet alleen sneller.

## Nieuwe functies

De tweede groep is een reeks plannen die we hebben gekozen maar nog niet begonnen. De meeste hebben eerst hetzelfde nodig: een verslag van wat er in elke match op de server gebeurt, zoals kills, doelen en waar spelers lopen. Dat verslag bouwen we één keer, en meerdere functies lezen eruit, in plaats van dat elke functie zijn eigen gegevens verzamelt.

- **2D-replays en hoogtepunten.** Bekijk elke match terug van bovenaf op de mapindeling, ronde voor ronde. Opvallende momenten, zoals een ace of een defuse op het laatste moment, worden automatisch uitgelicht.
- **Pings met locatie.** Markeer een vijand, een plek of een item voor je team, met de naam van het gebied waar de map die heeft. Op Ranked kun je alleen vijanden pingen die je echt ziet.
- **Een coach na de match.** Een paar cijfers uit je laatste match en één praktische tip, zoals waar je het vaakst stierf en uit welke richting. De tips schrijven we zelf, een voor een.
- **Heatmaps en een balansoverzicht.** Waar op elke map gevochten wordt en hoe elk wapen het over tijd doet, zodat balanswijzigingen op gegevens gebaseerd zijn en niet op gevoel.
- **Wekelijkse contracten en seizoenen.** Een paar uitdagingen per week en een seizoen van acht weken met een eigen ranglijst. Niets te koop en niets wat de gameplay beïnvloedt.
- **Vrienden en party's.** Voeg vrienden toe, zie waar ze spelen en doe mee, of volg een partyleider naar dezelfde server.
- **Slimmere bots op Unranked.** Bots die zich voorzichtig aanpassen aan hoe de mensen op de server het doen, en later de routes leren die echte spelers op elke map nemen.
- **Drukste tijden.** Een grafiek van wanneer de servers meestal vol zijn, en een optionele melding als er genoeg mensen online zijn.
- **Bugmeldingen in het spel.** Typ `/bug` met een korte beschrijving, en de melding komt bij het team met een screenshot en de details die nodig zijn om het na te spelen.

## Ook nog open

Easy Anti-Cheat, dat uit 0.34.0 werd gehouden, wacht nog op de laatste controle: een echte client die via de echte anti-cheat-bootstrapper als beschermd wordt bevestigd. Het komt uit zodra dat bevestigd is, en niet eerder.

## Jouw rol hierin

De volgorde van dit alles ligt niet vast. Is een van deze dingen belangrijker voor jou dan de rest, of mis je iets, laat het weten op [Discord](https://discord.gg/8kcHdg2Hch). De [roadmap](index.html#roadmap) toont wat er gaandeweg landt, en elk onderdeel krijgt een eigen devlogartikel als het zover is.
