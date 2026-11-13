---
title: Achter de schermen van 0.36.0, de update die je hoort
date: 2026-11-13
time: 14:30
summary: Voicechat, teampings, bots die de map lezen, een volledig vernieuwde audio en optioneel 128 updates per seconde. Dit is de lange versie: wat er veranderde, waarom we het zo bouwden, hoe we het testten en wat er nog komt.
image: img/media-village-yard.webp
tag: Release
version: 0.36.0
---
Versie 0.36.0 is uit, één dag na 0.35.0. Dat is geen toeval. Veel van het werk in deze update was bijna klaar toen 0.35.0 verscheen, en we kozen ervoor om het nog een dag extra te testen in plaats van het in de vorige release te proppen.

0.35.0 ging over vertrouwen: anti-cheat, geverifieerde statistieken, een launcher waarop je kunt rekenen. 0.36.0 gaat over gevoel. Het verandert hoe de game klinkt, hoe je team communiceert, hoe de bots bewegen en hoe vaak je game iets van de server hoort. De patch notes sommen elke wijziging op. Deze post legt de grote onderdelen uit, de keuzes erachter en hoe we ze testten, en hij is eerlijk over wat de update niet haalde.

> De launcher haalt 0.36.0 zelf binnen. Je instellingen blijven behouden. Wil je de nieuwe 128 updates per seconde proberen, dan vind je die onder Options > System > Network updates.

## Voicechat

TrueCombat was altijd al een game van callouts, en tot nu toe gebeurden die in aparte voice-apps. Vanaf 0.36.0 zit voicechat in de game zelf.

Het werkt als een squadradio. Hou **H** ingedrukt om via de radio met je team te praten. Tegenstanders horen dat nooit, waar ze ook staan. Hou **N** ingedrukt om hardop te spreken. Iedereen in je buurt hoort dat, ook de vijand, dus een fluistering achter een muur kan je verraden. We hielden die twee bewust gescheiden. Alleen een teamkanaal maakt van elke speler een perfecte communicator over de hele map. Alleen lokale stem maakt samenwerken onmogelijk. Samen geven ze je elke keer een keuze als je iets zegt.

![Een vuurgevecht op het erf van Village](img/media-village-yard.webp "Callouts zoals deze gebeuren nu in de game zelf: teamradio op H, lokale stem op N.")

De radio heeft een licht radio-effect dat je kunt uitschakelen. Onder **Options > Voice** kies je je microfoon, de versterking, push-to-talk of spraakactivatie met een instelbare drempel, en een lijst op het scherm van wie er praat. Met een microfoontest hoor je je eigen stem terug zonder iets te versturen. Je kunt afzonderlijke spelers dempen via het mute-menu, of het hele vijandelijke team.

Voice gebruikt Opus, dezelfde open codec waarop de meeste moderne voice-apps draaien, zodat het helder blijft bij een bescheiden bandbreedte. Servers beslissen zelf of ze voice inschakelen. Op de officiële servers staat het aan.

### Hoe we het testten

Voice is moeilijk te testen zonder een kamer vol mensen, dus bouwden we een test die er een speelt. Geautomatiseerde clients verbinden met een server, spreken vaste zinnen in op elk kanaal, en de test controleert wie wat hoort. De teamradio moet elke teamgenoot bereiken en niemand van het andere team. Lokale stem moet iedereen bereiken die dichtbij genoeg is, aan beide kanten. Ook de snelle chat uit het V-menu moet bij de juiste mensen aankomen. Die laatste controle vond vlak voor de freeze nog een echte bug: in Practice en free-for-all behandelde de game elke speler als toeschouwer en weigerde het V-menu. Dat is opgelost in deze release.

Wat de test ons niet kan vertellen, is hoe jouw microfoon klinkt via jouw headset in een echt potje. Daar hebben we jou voor nodig. Klinkt er iets niet goed, druk dan op F12 in de game en laat het ons weten.

## Teampings

Niet elke callout heeft een stem nodig. Druk op de **middelste muisknop** om een plek te markeren voor je team, of richt op een tegenstander om hem aan te wijzen. Je teamgenoten zien de markering vijf seconden, met een korte melding. Pings werken alleen in teammodi, en ze zijn beperkt zodat een nerveuze teamgenoot je scherm er niet mee kan volstoppen. Wil je de markeringen van anderen helemaal niet zien, dan verbergt `cg_pings 0` ze.

## Bots die de map lezen

Bots in Platinum waren altijd goed in één ding: richten. In alles wat een speler als een speler laat overkomen, waren ze een stuk zwakker. Ze namen elke ronde dezelfde route, liepen in een rij door deuropeningen, en draaiden zich om en vuurden zodra je in beeld kwam. 0.36.0 is de eerste grote stap om dat te veranderen.

- **Ze lezen de map.** Bots verspreiden zich nu over de verschillende routes naar een doel in plaats van elkaar te volgen. Ze nemen deuropeningen één voor één, vertragen om hoeken te checken en richten via het vizier als ze een hoek bewaken.
- **Ze hebben even tijd nodig om je te zien.** Een bot reageert niet meer op het moment dat je in zijn zicht komt. Hoe snel hij je opmerkt, hangt af van de afstand, het licht, of je beweegt, en of je staat, hurkt of ligt. Wie over een open straat sprint, valt op. Wie door een donkere tuin kruipt, vaak niet.
- **Ze kamperen niet meer bij spawns.** Bots houden de uitgangen van je spawn niet meer bezet.
- **Ze hebben een persoonlijkheid.** Elke bot komt nu uit een selectie van 32, elk met een eigen naam, een speelstijl ergens tussen roekeloos en voorzichtig, en favoriete wapens.
- **Ze praten.** Bots melden vijandelijke posities met de naam van de plek in de teamchat, en laten weten wanneer de bom geplant is of een vlag genomen is. Wil je dat ze stiller zijn, dan regelt `bot_chat` hoeveel ze zeggen.
- **Ze luisteren.** Typ "follow me", "hold here" of "push" in de teamchat en bots in de buurt reageren. Vraag een bot of hij een bot is, en hij zegt altijd de waarheid.
- **Ze houden potjes spannend.** Zijn er echte spelers in de game, dan passen bots hun niveau aan zodat de stand dicht bij elkaar blijft. Met `bot_adaptive 0` zetten serverbeheerders dat uit als ze een vaste moeilijkheid verkiezen.

We testten de bots zoals we alles testen: in volledige botpotjes op elke map, met vaste controles voor routes, deuropeningen, reactietijd en chat, en met een echte speler in de game. Die laatste test toonde één ding dat nog niet goed zit. Bots proberen uit de vuurlijn van een teamgenoot te stappen, maar als een muur de kant blokkeert die ze kiezen, gaan ze te traag opzij. De oplossing wordt getest voor de volgende update.

## De audio, volledig vernieuwd

Geluid is de helft van een tactische shooter. Je hoort een speler voor je hem ziet, en je hoort waar hij is. De originele engine was gebouwd voor de hardware van 2003, en dat merkte je: in een druk vuurgevecht vielen geluiden gewoon weg zodra er te veel tegelijk speelden, en vaak waren dat net de geluiden die je nodig had.

0.36.0 bouwt de mix van de grond af opnieuw op.

- **Twee keer zoveel geluiden tegelijk.** De game kan nu twee keer zoveel geluiden tegelijk afspelen. Moet hij toch kiezen, dan kiest hij bewust: vijandelijke voetstappen en geweervuur winnen het van achtergrondgeluid en vallende hulzen.
- **Een evenwichtige mix.** Elk geluid in de game werd gemeten en op volume gebracht, categorie per categorie, zodat een pistool niet meer per ongeluk luider is dan een geweer. Een limiter op de uitgang voorkomt dat luide momenten vervormen.
- **Geweervuur krijgt het podium.** Schoten en explosies dichtbij dempen de rest van de mix even, zodat ze erdoor komen zoals het hoort. Je kunt instellen hoe sterk dat effect is.
- **Natuurlijke variatie.** Voetstappen, geweervuur, inslagen en hulzen variëren nu licht in toonhoogte, zodat de tiende voetstap niet meer klinkt als een kopie van de eerste.
- **Kogels die je hoort.** Kogels die vlak langs je gaan, knallen en suizen voorbij. Je weet dat er op je geschoten wordt, en ongeveer van waar, nog voor je een inslag ziet.
- **De nasleep van een explosie.** Een explosie dichtbij dempt je gehoor even en komt binnen met een lage dreun. Het fluiten in je oren is nu een zachtere toon. De originele piep blijft beschikbaar voor wie die verkiest.

Alles wat nieuw is, heeft een instelling op de nieuwe pagina **Options > Audio**.

## Online spelen: 64 of 128 updates per seconde

Dit is de wijziging die de meeste spelers nooit in een menu zullen zien, en de wijziging die we het langst hebben gemeten.

Je game ziet de andere spelers niet rechtstreeks. Hij ziet een reeks snapshots van de server, elk een beeld van de wereld op één moment, en vult de gaten daartussen zelf in. Hoe meer snapshots er per seconde binnenkomen, hoe beter wat jij ziet overeenkomt met wat de server ziet. Tot nu toe vroeg de launcher er 40 per seconde.

Vanaf 0.36.0 is de standaard **64**. Op servers die op 128 ticks draaien, kun je **128** kiezen onder **Options > System > Network updates**. 64 blijft de standaard met een reden: 128 verdubbelt ongeveer de hoeveelheid data die je ontvangt, tot zo'n 45 à 65 KB/s in een vol potje, en niet elke verbinding wil dat. Kan de jouwe het aan, probeer het dan.

Meer snapshots versturen was het makkelijke deel. Ze een echte internetverbinding laten overleven, was dat niet. Elke snapshot wordt verstuurd als een wijziging ten opzichte van een eerdere, en de originele engine onthield maar een korte geschiedenis van eerdere snapshots. Bij 128 per seconde volstond een korte lagpiek om van het einde van die geschiedenis te vallen, en dan moest de game opnieuw beginnen met een volledige snapshot van de hele wereld. In een test met 250 ms vertraging gebeurde dat 286 keer per minuut. 0.36.0 houdt een langere geschiedenis bij, en in dezelfde test gebeurde het nul keer.

We ontdekten ook dat servers op Windows de 128 ticks niet echt haalden. Windows wekt slapende programma's standaard op met een grove timer, waardoor een server die 128 snapshots per seconde wilde versturen er ongeveer 70 haalde. Dedicated servers vragen Windows nu om een fijne timer en houden hun volle tempo vast. Dat is belangrijk voor iedereen die een server op zijn eigen pc host.

De eindcijfers, op een volle 128-tickserver met vijftien bots en één echte speler: 127,6 snapshots per seconde ontvangen op de instelling 128, 63,6 op 64, en 126,2 op een verbinding met 60 ms vertraging en één procent pakketverlies. Geen enkele snapshot kwam te laat binnen om nog bruikbaar te zijn.

### Treffers die kloppen met de server

Ook twee oudere problemen zijn opgelost. Ten eerste beslist je game nu met precies dezelfde regels als de server of hij een hitmarker toont, zodat de marker en de server het eens zijn. Ten tweede tellen hoofden en benen die in bepaalde hoeken en houdingen buiten de hitbox van een speler steken nu mee. Vroeger konden schoten op een leunend hoofd of een uitgestrekt been missen, terwijl ze op jouw scherm duidelijk raak waren.

Om beide te controleren, vuurden we honderd schoten op verschillende delen van het lichaam vanuit elke houding en vergeleken we wat de game toonde met wat de server telde: honderd op honderd kwamen overeen. Daarna herhaalden we de test over 160 gesimuleerde slechte verbindingen met vertraging, jitter en pakketverlies.

Er is ook een nieuwe netgrafiek, `cg_netGraph 3`. Die toont je ping, pakketverlies in beide richtingen, snapshots per seconde, gaten tussen snapshots en hoe vaak je game zijn voorspelling moest bijsturen. Voelt je verbinding ooit verkeerd aan, dan vertelt een screenshot van die grafiek ons meer dan welke beschrijving ook.

> Eén beperking: demo's die met 128 updates per seconde zijn opgenomen, spelen in oudere versies van de game mogelijk niet volledig af.

## Naamkleuren

De launcher heeft nu een echte kleurkiezer voor je naam, onder **Settings > Controls > Player > Name colours**. Selecteer letters door te klikken en te slepen, kies een kleur en zie het resultaat meteen. Gekleurde namen worden nu ook overal in de game correct getoond: op het scorebord, in de chat en in het Deployment Menu, met elke kleur die de game kent, niet alleen de eerste tien.

## Een installatiemap die even groot blijft

Een speler wees ons erop dat zijn installatiemap bij elke update groeide. Hij had gelijk. Onder DirectX 12 bewaart de game gecompileerde shaders zodat maps de volgende keer sneller laden, en hij bewaarde een nieuwe kopie bij elke mapwissel en elke server. Na een paar weken kon dat oplopen tot enkele gigabytes.

De cache houdt nu één kopie bij die over maps en servers heen hergebruikt wordt. De launcher houdt ook caches, replays, screenshots en bugrapporten onder een maximale grootte en verwijdert eerst de oudste bestanden. **Settings > Storage** toont hoeveel ruimte elk ervan inneemt. De eerste start van de nieuwe launcher ruimt een te grote cache van eerdere versies op, en updates wissen de shadercache niet langer twee keer, zodat je eerste potje na een update sneller laadt.

## F12-rapporten, rechtstreeks naar ons

Sinds 0.35.0 bewaart F12 een bugrapport met een screenshot. Vanaf 0.36.0 komt dat rapport ook rechtstreeks bij het ontwikkelteam terecht, met de details die we nodig hebben om het probleem te vinden: de map, je positie, de server, de build en een paar regels uit je console. Hardwaregegevens zijn optioneel. Elk rapport wordt nog steeds op je pc bewaard, en als versturen mislukt, laat de game je dat weten en houdt hij het bij. Hou je je rapporten liever voor jezelf, dan regelt `cg_bugReportUpload 0` dat.

Dit is het nuttigste wat je voor de game kunt doen. Een rapport dat je verstuurt op het moment dat er iets misgaat, vanaf de exacte plek waar het gebeurde, bespaart ons uren.

## Beveiliging

We hebben onze beveiligingsmaatregelen in deze update aangescherpt en uitgebreid. Zoals altijd gaan we niet in detail in op hoe.

## Fixes

Twee punten uit de lijst "wat de update niet haalde" in onze post over 0.35.0 zijn opgelost:

- **Het red-dotvizier.** Het M68-vizier op de M4 SOPMOD toont nu een scherpe rode stip als je richt. Vroeger was dat een wazig vierkant.
- **Instant replay.** F8-clips hebben minstens vijf seconden spel nodig, en de melding "Clip saved" toont de echte lengte van de clip.

En een aantal kleinere:

- Options > System > Calibrate Brightness opent weer.
- Je eigen schoten spelen het juiste geluid af voor het wapen dat je vasthoudt.
- Toeschouwers blijven toeschouwer na een mapwissel of herstart, in plaats van in een team te worden gezet.
- Voetstappen en het meebewegen van het beeld volgen omgeschakeld wandelen en sprinten correct.
- In de serverbrowser werkt Reconnect weer na een verkeerd wachtwoord, en meedoen aan een lopend potje via de browser in de game werkt.
- Neemt een DLSS-override in de NVIDIA App het over, dan meldt de game dat nu, in plaats van stil te falen.

## Hoe we het testten

Elke kandidaat-build gaat door dezelfde poort: een volledige regressietest van de game en de dedicated server op DirectX 12 en OpenGL, negentien geautomatiseerde controles in totaal, van gameplay en hitregistratie tot instellingen, herstarts, de launcher en de grootte van de installatiemap. Daarbovenop komen de live-controles: de test met honderd schoten, 160 gesimuleerde slechte verbindingen, voice in team- en free-for-allmodi, de serverbrowser, botpotjes en voor deze update de test met 128 snapshots.

Er waren tien kandidaat-builds nodig om hier te komen. Elke build vond wel iets: een verouderd menubestand dat de nieuwe Audio-pagina verborg, een test die Practice niet dekte, een schijf die tijdens één run zo druk was dat een testclient de verbinding verloor. Elke fout werd tot op de oorzaak uitgezocht voor we verdergingen. De tiende build doorstond alles en werd op 13 november verpakt en gepubliceerd.

## Wat de update niet haalde

Sommig werk was dichtbij maar nog niet klaar, en dat zeggen we liever dan het stil te laten.

- **Hoe wapens aanvoelen.** Een ronde afstelling van hoe wapens aanvoelen bij het vuren is gebouwd, maar heeft meer playtests nodig voor ze verschijnt.
- **Slimmere bots, deel twee.** De vuurlijnfix die we hierboven beschreven, en de volgende stap in hoe bots als team samenwerken.
- **Een nieuwe look voor menu's en HUD.** Een volledige vernieuwing van elk menu en de HUD in de game wordt getest, met de huidige HUD als optie.
- **Visuele en gebruiksvriendelijke verbeteringen.** Een reeks kleinere visuele en praktische aanpassingen in de game en de launcher.

Die staan gepland voor de volgende update, en ze verschijnen wanneer ze door dezelfde poort raken als alles hierboven, niet eerder. De [roadmap](index.html#roadmap) toont het volledige plan.

## Bedankt

Bijna alles in deze update begon bij een speler: een vraag naar ingebouwde voice, een klacht dat bots robotachtig aanvoelden, een vraag over een groeiende installatiemap. Bedankt om te spelen, te melden en geduldig te zijn terwijl we het goed kregen.

Voelt er iets niet goed aan in 0.36.0, druk dan op F12 in de game of laat het ons weten op [Discord](https://discord.gg/8kcHdg2Hch). Tot op de servers.
