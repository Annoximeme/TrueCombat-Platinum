---
title: Wedstrijdmodus, gebouwd voor clanavonden
date: 2026-11-07
summary: Clanwedstrijden waren het hart van TC:E. Platinum 0.32 brengt een volledig wedstrijdverloop naar elke server, met een pauze die de hele wereld bevriest.
image: img/media-deployment.webp
tag: Competitief
version: 0.32.0
---
Vraag iemand die TC:E serieus speelde wat er is bijgebleven, en het is zelden een publieke server. Het is een clanwedstrijd: twee tags, een geboekte server, en een ronde die beslist wordt door één goed verdedigde hoek. Platinum 0.32 brengt dat formaat terug als ingebouwde wedstrijdmodus, klaar op elke server met één commando.

## Het verloop

Een wedstrijd begint met de **warm-up**: vrij spelen met respawns, en zonder automatische teamverdeling, zodat clans zich kunnen opstellen zoals ze willen, vier tegen vijf inbegrepen. Spelers typen `ready` als ze klaar zijn, en de wedstrijd begint zodra iedereen in beide teams klaar is. Bots houden niets op.

Daarna volgt de **messenronde**. Eén ronde, alleen messen, geen respawns in welke modus dan ook, twee minuten op de klok. De bom en de vlaggen blijven buiten spel. De winnaars kiezen hun kant met `stay` of `swap`.

Dan gaat de wedstrijd **live**: twaalf rondes in de rondemodi, of twee helften van 20 minuten in Team Deathmatch en Flag Capture. De teams liggen vast, en elke kill uit de warm-up en de messenronde verdwijnt van het scorebord en uit het rapport voor de ranglijsten. Bij **rust** wisselen de teams van kant, en scores, clannamen en resterende time-outs gaan mee. Een team dat niet meer in te halen is, wint meteen.

## Een pauze die echt pauzeert

Het lastigste onderdeel was de time-out. Een tactische time-out is alleen eerlijk als er niets beweegt, dus in Platinum bevriest de hele wedstrijd. Spelers staan stil, granaten hangen in de lucht met hun lont vastgehouden, en de rondeklok, de bomtimer, gevallen rugzakken, herlaadacties en respawngolven houden allemaal precies de tijd die ze nog hadden. Na een aftelling van vijf seconden gaat het spel verder.

Elk team krijgt standaard twee time-outs van 60 seconden. Admins kunnen zonder tijdslimiet pauzeren.

## Gebouwd om getest te worden

De wedstrijdmodus doorliep dertien geautomatiseerde teststappen met twee echte spelclients, op zowel DirectX 12 als OpenGL. Daaronder: een messenronde die echt alleen messen toelaat, een kantkeuze die alleen de winnaars kunnen maken, een rondeklok die tien seconden pauze vasthield, een rookgranaat waarvan de lont alleen brandde terwijl het spel liep, en een rustwissel die scores en namen meenam.

## Organiseer je eigen wedstrijd

Host een server in een teammodus, typ `match on` in de serverconsole, geef de teams een naam en laat beide kanten zich klaarmelden. De [competitieve pagina](competitive.html) noemt elk commando en elke instelling. Wedstrijdavonden en scrims worden georganiseerd op onze Discord.
