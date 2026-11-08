---
title: Wat de officiële servers draaiende houdt
date: 2026-11-08
summary: Twee officiële servers, een masterlijst, live ranglijsten en deze website draaien dag en nacht. Dit gebeurt er achter de schermen als niemand kijkt.
image: img/map-northport.webp
tag: Servers
---
Als je op een officiële Platinum-server komt, zie je een map, een scorebord en andere spelers. Daarachter zit een kleine set diensten die dag en nacht moet blijven draaien, of er nu iemand van het team wakker is of niet. In dit artikel lopen we langs wat dat is en hoe we erop letten.

## Wat waar draait

Alles wat publiek is, draait op één server in een Europees datacenter:

- **Officiële #1 Ranked.** Elk potje telt mee voor de [ranglijsten](leaderboards.html).
- **Officiële #2 Unranked.** Tien bots houden de server levend, zodat er altijd iemand is om tegen te spelen. Potjes hier raken je rating nooit.
- **De masterserver**, die de serverlijst in het spel en de launcher vertelt welke servers er zijn.
- **De statistiekendienst** achter de ranglijsten, spelersprofielen en de live scoreborden op de [serverpagina](servers.html).
- **Deze website**, die zichzelf elke twee minuten bijwerkt vanuit onze coderepository en elke pagina via HTTPS aanbiedt.

De twee gameservers draaien los van elkaar, elk met eigen instellingen en een eigen map, zodat een probleem op de ene de andere niet kan meenemen.

## Een waakhond die nooit slaapt

Elke minuut vraagt een waakhond elke gameserver om zijn status, net zoals de serverlijst dat doet. Mist een server drie antwoorden op rij, dan wordt hij automatisch herstart en krijgt het team een melding op Discord. Een crash geeft dezelfde melding. In de test was een server die hard werd afgeschoten binnen elf seconden weer online.

Dezelfde controle houdt de rest in de gaten: dat de servers op de masterserver staan, dat de website en de statistiekendienst antwoorden, en dat schijfruimte en geheugen in orde zijn. Blijft een server falen, dan stopt de waakhond na vier pogingen in een uur met herstarten en wacht hij tot een mens kijkt, zodat een dieper probleem nooit een eindeloze herstartlus wordt.

## De nachtronde

Elke nacht doet het systeem een korte ronde. Het controleert dat elke map in de rotatie echt geïnstalleerd is, stuurt een kort gezondheidsrapport naar het team, en herstart een gameserver voor een schone start, maar alleen als er geen menselijke spelers op zitten. Niemand wordt voor onderhoud uit een potje gezet.

## Back-ups die het gebouw verlaten

Een back-up op dezelfde machine is geen back-up. Elke nacht worden de serverconfiguratie, de wedstrijdgegevens en de statistiekendatabase gekopieerd naar een privé-repository op een andere plek. Alles wat gevoelig is, zoals wachtwoorden en ondertekeningssleutels, wordt versleuteld voordat het de server verlaat. Er wordt alleen een kopie gemaakt als er echt iets veranderd is, zodat de geschiedenis leesbaar blijft.

> Een back-up telt pas als je zeker weet dat je hem terug kunt halen. We hebben het ontsleutelen van de externe kopie getest voordat we het klaar noemden.

## Waarom het ertoe doet

Rangen, ratings en wedstrijdgeschiedenis zijn van jou. Je hebt ze verdiend, en ze mogen niet verdwijnen omdat een schijf het begaf of een instelling misging. En een officiële server die om negen uur 's avonds plat ligt, is een clanavond die niet doorgaat. Niets hiervan is glamoureus, maar het is het deel van het spel dat elke dag moet werken.
