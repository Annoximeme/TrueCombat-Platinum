---
title: De weg vooruit, voluit
date: 2026-11-11
summary: De volgende twee updates zijn gepland, en het werk erachter ook. Een herbouwde bewegingskern, een matchverslag dat replays en coaching mogelijk maakt, bots die moeten kijken en luisteren zoals jij, pick-ups op Discord en meer. Dit is de lange versie, met hoe elk onderdeel werkt en waarom we het zo bouwen.
image: img/map-delta.webp
tag: Roadmap
---
Twee dagen geleden publiceerden we [Waar we hierna aan werken](devlog-whats-next.html) en [Wat de playtests ons leerden](devlog-playtest-fixes.html). Sindsdien is het plan van een lijst een werkvolgorde geworden: we weten wat in de volgende update zit, wat in die daarna, en hoe de grotere projecten erachter eruitzien.

Deze post is de lange versie. Hij herhaalt de twee eerdere lijsten niet. Hij legt uit hoe de belangrijkste onderdelen werken, want een aantal ervan zijn dingen waarvoor een spel van deze leeftijd nooit ontworpen is, en een opsommingsteken doet ze geen recht. Het is een lange tekst, dus gebruik de inhoudslijst om naar het deel te springen dat je interesseert.

> Niets in deze post heeft een datum. Een update komt uit als elk onderdeel door de volledige testronde komt, op het spel, de server, beide renderers en de launcher. Waar iets afhangt van een partij buiten ons team, zeggen we dat erbij.

## Hoe het werk is ingedeeld

Er staan twee updates in het plan, en ze hebben bewust een ander karakter.

**Update 0.35** gaat over hoe het spel speelt. Ze bevat de kernfixes uit de playtests, en de eerste nieuwe functies die geen verzamelde gegevens nodig hebben om te werken.

**Update 0.36** gaat over bots, maps en de opwarmfase, plus de functies die uit opgenomen matches lezen. Die functies hebben eerst echte matches nodig, en daarom komen ze als tweede: het opnemen begint met 0.35, en 0.36 bouwt voort op wat er dan verzameld is.

Binnen 0.35 worden de fixes eerst gebouwd. Als de update kleiner moet worden om de fixes sneller uit te brengen, schuiven de nieuwe functies op, nooit de fixes.

## Update 0.35: wat het onderzoek opleverde

Toen we de playtestrapporten regel voor regel naast de broncode legden, verklaarde één vaststelling meer dan alle andere.

De spelcode van Platinum is niet de originele TC:E-code met wijzigingen erbovenop. Het is een nieuwe, eigen implementatie, geschreven om zich te gedragen als het origineel. Dat maakt de DirectX 12-renderer, de lagcompensatie en de bots überhaupt mogelijk. Het betekent ook dat sommige dingen die spelers als bug meldden geen kapotte functies zijn. Het zijn functies die nog niet herbouwd zijn, of die als eerste benadering gebouwd zijn en nooit vervangen werden.

### Beweging heeft één oorzaak

Springafstand, hurksnelheid, laddersnelheid, voetstappen en het wiebelen van het beeld werden als aparte problemen gemeld. Het is één probleem. Het stuk code dat een speler elk frame door de wereld beweegt, met wrijving, versnelling, treden en hellingen, is nog de voorlopige versie uit de vroege ontwikkeling. Alles wat van je snelheid afhangt, erft de kleine fouten ervan: wanneer een voetstap klinkt, hoeveel het beeld beweegt, hoe ver een sprong draagt.

We vonden ook een concrete fout in de sprong zelf. Een sprong uit beweging verliest een groot deel van zijn hoogte tegenover een sprong uit stilstand, en daardoor is de sprong op de container op Delta nu onmogelijk.

We gaan die waarden dus niet één voor één bijstellen. De voorlopige bewegingskern wordt vervangen door een getrouwe, en daarna wordt elke waarde gemeten tegenover het originele spel: spronghoogte, sprongafstand bij lopen en sprinten, de snelheid bij hurken en gehurkt lopen, laddersnelheid, hoe hoog een rand mag zijn om erop te klimmen. We hebben een testopstelling die dezelfde invoer door het origineel en door Platinum stuurt en de resultaten vergelijkt, zodat "voelt juist" een getal wordt dat we na elke wijziging kunnen nakijken.

Ook de nauwkeurigheid van wapens hangt hiervan af. De straf op nauwkeurigheid bij bewegen wordt uit je snelheid berekend, dus elk wapen wordt opnieuw gecontroleerd zodra de nieuwe beweging erin zit.

### Gunplay, gemeten

Voor treffers op afstand en schoten die naast het richtpunt landen, bouwen we een schietbaan die vanzelf draait: vaste doelen op 10, 25, 50 en 100 meter, elk wapen in het arsenaal, gericht via het vizier en vanuit de heup, op een perfecte verbinding en op een vertraagde. Ze legt vast waar elke kogel landt tegenover het vizier en vergelijkt dat met het origineel. Wat die gegevens tonen, wordt opgelost, voor het hele arsenaal en niet alleen voor de wapens die in meldingen genoemd werden.

Dezelfde ronde omvat de schade per lichaamsdeel voor elk wapen, het tempo van het grendelgeweer en de wapengeluiden, ook de geluiden die je als toeschouwer hoort.

### Oorzaken die we al bevestigd hebben

- **Een granaatworp die je wapen afvuurt.** Na je laatste granaat schakelde het spel meteen terug naar je wapen, zonder de normale wisselvertraging, zodat een muisknop die nog ingedrukt was direct vuurde. De fix voegt de vertraging toe en vraagt een nieuwe druk op de trekker.
- **Geluiddempers.** Je kunt een demper kiezen in het Deployment Menu, maar niets in de vuur- of geluidscode leest die keuze al. Hij krijgt een gedempt geluid, geen mondingsflits en een kortere afstand waarop bots hem kunnen horen.
- **Granaten vasthouden.** Granaten worden nu gegooid zodra je de knop indrukt. Het originele gedrag keert terug: inhouden om scherp te stellen, loslaten om te gooien, terwijl de lont loopt zolang je vasthoudt.
- **Je team tussen maps.** Het spel onthield niet in welk team je zat als de map wisselde. Dat doet het straks wel, en het bewaart ook je team en je score als je wegvalt en binnen enkele minuten terugkomt.

### Al het andere in de fixronde van 0.35

- Invoer voor chat en teamchat, met geschiedenis.
- Teamkeuze die bij de eerste klik registreert.
- Een serverbrowser in het spel, in het Esc-menu, zodat je van server kunt wisselen zonder terug te gaan naar de launcher.
- Het menu voor spraakcommando's.
- Gekleurde spelersnamen die een herstart overleven en overal hetzelfde getoond worden.
- Toetsen toewijzen aan extra muisknoppen, en schakelopties voor wandelen en sprinten.
- Een pagina Opties in het Esc-menu: muis- en richtgevoeligheid met getypte waarden, gezichtsveld, geluidsvolumes en HUD-opties, allemaal meteen toegepast.
- Een instelling voor de hitmarker. Op Unranked kiest de speler, op Ranked staat hij altijd uit.
- Een langere, instelbare killfeed met namen in teamkleur.
- Deuren die de instellingen van elke map volgen zoals in het origineel, met een aanwijzing op het scherm.
- Flitsgranaten die bots even lang verblinden en verdoven als een speler.
- Valschade op de benen, zoals in het origineel.
- Ontbrekende wapens in het Deployment Menu, te donkere red dots en verkeerd gekleurde wapenonderdelen.

### Een bugmelder in het spel zelf

Druk op F12, of kies "Een bug melden" in het Esc-menu, en er opent een tekstvak. Geen console, geen commando om te onthouden. De melding vertrekt met wat we nodig hebben om het probleem na te spelen: de map, je positie, de server, de build, de renderer, een screenshot en de laatste regels van het spellogboek. Gegevens over je hardware gaan alleen mee als je het vinkje laat staan, en je ziet precies wat er verstuurd wordt.

We willen dit in 0.35 om een egoïstische reden: de feedback van de volgende playtests moet hierlangs binnenkomen, met bij elke melding een positie en een screenshot.

## Het matchverslag

Dit is het onderdeel waar de meeste nieuwe functies op steunen, dus het verdient een degelijke uitleg.

Vanaf 0.35 schrijven de officiële servers op wat er in elke match gebeurt: elke kill, elk punt schade, elk doel, het begin en einde van elke ronde, en waar elke speler zich bevindt, enkele keren per seconde gemeten. Het is een compact logboek van het spelverloop, een paar honderd kilobyte per match, dat een beperkte tijd bewaard en daarna gewist wordt. Het legt vast wat er in de match gebeurt en niets over jou daarbuiten.

Oudere spellen beschouwden een match als voorbij zodra het scorebord sluit. Met zo'n verslag wordt een match iets dat je achteraf kunt bestuderen. Eén opname voedt veel functies:

- **2D-replays.** Bekijk elke match van bovenaf op de plattegrond van de map, ronde per ronde, met een tijdlijn en de killfeed.
- **Automatische hoogtepunten.** De server herkent een ace, een clutch, meerdere kills binnen enkele seconden of een bom die op het nippertje onschadelijk gemaakt wordt, en kiest de beste momenten.
- **Heatmaps.** Waar gevochten wordt en waar spelers sneuvelen op elke map, per team en per modus.
- **Een publiek balansoverzicht.** Hoe elk wapen het over tijd doet: tijd tot een kill, aandeel hoofdschoten, hoe vaak het gekozen wordt. Over balans kan dan gediscussieerd worden met gegevens die iedereen kan zien.
- **Een coach na de match.** Enkele cijfers uit je laatste match en één praktische tip, zoals het gebied waar je het vaakst stierf en of dat van voren of van opzij was. De tips schrijven we zelf, één voor één. Geen gegenereerde tekst.
- **Wekelijkse contracten en seizoenen.** Kleine wekelijkse uitdagingen en een seizoen van acht weken met een eigen ranglijst. Niets te koop en niets dat het spel beïnvloedt.
- **Bots die leren.** Daarover verderop meer.

We bouwen het verslag één keer en laten elke functie eruit lezen, in plaats van elke functie op haar eigen manier gegevens te laten verzamelen. Het opnemen komt in 0.35. De functies die eruit lezen volgen in 0.36, als er genoeg matches zijn om ze zinvol te maken.

## Ook nieuw in 0.35

Drie functies die geen verzamelde gegevens nodig hebben, komen mee met de eerste update.

### Pings met locatie

Richt op iets, druk op de pingtoets, en je team ziet een markering in de wereld en een regel in de chat met de naam van het gebied, zoals "[Markt] Vijand gezien". Twee keer tikken betekent "vijand hier", en een klein wiel biedt de rest: hulp nodig, ik ga hierheen, ik verdedig, bom of vlag.

Twee details zijn belangrijk. Ten eerste controleert de server of je een vijand echt kunt zien voor hij een vijandping aanvaardt, zodat pings nooit iemand door een muur kunnen verraden, op Ranked of elders. Ten tweede bevatten de meeste originele maps helemaal geen gebiedsnamen, dus leiden we die af uit de indeling van de map en benoemen we ze met de hand, te beginnen met Village.

### Bots die zich aanpassen aan de server

Op Unranked vergelijkt de server elke minuut hoe de menselijke spelers het doen tegenover de bots, en stelt hij het richten en de reactietijd van de bots een klein beetje bij, naar boven of naar beneden. De stappen zijn klein en gelijkmatig, zodat je het nooit zou mogen merken. Je merkt alleen dat een server vol nieuwkomers niet afgeslacht wordt en dat een server vol veteranen zich niet verveelt. Ranked heeft geen bots, dus daar geldt dit niet.

### Wanneer er gespeeld wordt

De servers weten al hoeveel spelers online zijn. Ze gaan die geschiedenis bijhouden en er op de website een grafiek met de drukste momenten van maken. De launcher en Discord krijgen een optionele melding: geef een aantal op, en je krijgt een seintje als er zoveel spelers online zijn. Voor een kleine community is weten wanneer je moet opdagen de helft van een volle server.

## Bots, herbouwd vanaf de zintuigen

De bots van Platinum kunnen bewegen, schieten, voor het doel spelen en in duo's werken. De playtests waren duidelijk over wat ze niet kunnen: ze nemen dezelfde routes, ze richten zelden via het vizier, ze leunen op de verkeerde momenten, en hun reacties schommelen tussen traag en ogenblikkelijk. We zouden die vier dingen kunnen oplappen. In plaats daarvan hebben we een nieuw botbrein ontworpen in vier lagen, en de eerste laag wordt nu gebouwd voor 0.36.

### 1. Een bot die de map begrijpt

De originele maps bevatten geen informatie voor bots. Platinum rekent al uit waar een bot kan lopen. De volgende stap is uitrekenen wat een plek *betekent*.

Als een map laadt, verdeelt het spel hem in een paar honderd kleine gebieden en berekent het welke gebieden elkaar kunnen zien. Uit die ene tabel volgt heel wat, zonder dat iemand een map met de hand moet markeren:

- **Blootstelling.** Een gebied dat vanuit veel andere te zien is, is gevaarlijk om in te staan. Een gebied dat weinig andere zien, is een plek om te houden.
- **Dekking.** Voor elke plek: welke richtingen beschermd zijn, en of je ervoor moet hurken.
- **Flessenhalzen.** De gebieden waar elke route tussen een spawn en een doel doorheen moet.
- **Hoeken.** De plekken waar één stap opzij plots een groot stuk van de map blootlegt. Daar vertraagt een speler, brengt hij het vizier omhoog en leunt hij, dus daar gaan bots het ook doen: op hoofdhoogte op de rand richten voor ze de hoek om komen, en naar de open kant leunen als ze hem houden.
- **Banen.** Tot vier duidelijk verschillende routes tussen elke spawn en elk doel. Bots worden bij het begin van een ronde over de banen verdeeld, met een maximum per baan, zodat ze niet meer in één groep bij dezelfde deur aankomen. Bij smalle deuropeningen komt er een wachtrij in plaats van een opstopping.

Omdat het uit de geometrie berekend wordt, werkt het op elke map, ook op communitymaps die we nooit gezien hebben.

### 2. Een bot die moet kijken en luisteren

Dit is de laag die het meest verandert aan hoe bots aanvoelen.

Vandaag is een bot zich van je bewust op het moment dat er niets tussen jullie in staat. Daarom voelen hun reacties het ene moment oneerlijk en het andere blind. In het nieuwe ontwerp neemt een bot de wereld ongeveer waar zoals jij:

- **Opmerken kost tijd.** Bewustzijn bouwt zich op. Snel als je dichtbij bent, recht voor de bot en in het open veld. Traag als je ver weg bent, aan de rand van zijn blikveld, stilstaat of in de schaduw staat. Een bot kan je over het hoofd zien, en je kunt het zien gebeuren.
- **Horen.** Voetstappen, herladen en deuren vertellen een bot ongeveer waar iets is, niet precies waar. Stil lopen wordt een echte tactiek tegen bots, zoals tegen mensen.
- **Vermoeden, niet weten.** Elk team bots houdt een gedeeld beeld bij van waar de vijand *zou kunnen* zijn, alleen opgebouwd uit wat zijn leden gezien en gehoord hebben. Het vervaagt en verspreidt zich met de tijd. Een bot controleert de hoek waar hij je het laatst zag, niet de hoek waar je echt bent.
- **Beslissen door af te wegen.** In plaats van een vast script geeft een bot een score aan een kleine reeks acties, zoals doordrukken, houden, flankeren, terugtrekken, een teamgenoot steunen of voor het doel gaan, afhankelijk van de situatie waarin hij denkt te zitten.
- **Persoonlijkheden.** Elke botnaam krijgt een eigen temperament: geduldig of agressief, een favoriete afstand, hoe snel hij een risico neemt. Dezelfde naam speelt van match tot match herkenbaar op dezelfde manier.
- **Zenuwen.** Een bot die alleen tegenover drie staat, speelt anders dan een bot in een winnend team, en bots maken af en toe een geloofwaardige fout.

### 3. Een team dat een plan maakt

Bij het begin van een ronde kiest een team bots een plan uit een klein draaiboek: welke banen ze nemen, wie houdt en wie doordrukt. Het team houdt bij welke plannen op deze map tegen deze tegenstanders gewerkt hebben en gaat die geleidelijk verkiezen, terwijl het de andere af en toe blijft proberen om niet voorspelbaar te worden.

Bots melden wat ze zien via dezelfde spraakcommando's en pings die spelers gebruiken, met gebiedsnamen, en reageren op meldingen van teamgenoten. Dat werkt in twee richtingen: je zult een bot een eenvoudig bevel kunnen geven, zoals volg mij of houd deze plek.

### 4. Bots die leren van echte matches

Hier komt het matchverslag terug. Zodra er op een map genoeg matches opgenomen zijn, kunnen bots die gebruiken:

- **Routes.** Bots verkiezen de paden die echte spelers op elke map werkelijk nemen, gemengd met hun eigen baan, zodat ze flankeren en houden waar mensen dat doen.
- **Posities en timing.** Waar spelers doorgaans post vatten, en hoelang na het begin van een ronde de gevechten in elk gebied meestal losbarsten.
- **Richten.** Hoe een mensenhand een vizier echt naar een doel brengt: de snelheid, het doorschieten, het tot rust komen. Het richten van bots volgt die curves in plaats van een verzonnen formule.

We ontwerpen ook een optionele modus voor later, waarin een bot kan spelen in de stijl van een specifieke speler die daarmee ingestemd heeft.

Hier zit nergens een chatbot in. De beslissingen van een bot worden genomen door spellogica die op de server draait en getest en gemeten kan worden, niet door een taalmodel.

### Hoe we weten of het gelukt is

Elke wijziging aan de bots wordt nu al getest met volledige matches op alle zes de maps, oude versie tegen nieuwe, waarna we de cijfers vergelijken. Voor dit werk voegen we een maat toe voor hoe menselijk de bots eruitzien: hoe vaak ze het vizier gebruiken, hoeveel verschillende routes een team per ronde neemt, hoe hun reactietijden verdeeld zijn.

En zodra de latere lagen erin zitten, willen we een aangekondigde testavond houden op de officiële servers waarop spelers raden wie in de match een bot was. Als je het niet kunt zeggen, zijn we klaar.

De eerste laag, het begrip van de map met hoeken en banen, is in ontwikkeling voor 0.36. De andere drie volgen één voor één, telkens nadat de vorige zich bewezen heeft.

## Online spelen en launcher 1.5.0

Dit werk is gebouwd en bijgewerkt naar de huidige versie. Wat het nog nodig heeft, is zijn test met echte spelers op echte verbindingen, en het komt in een update zodra het daardoor is.

- **Een verbinding die je kunt aflezen.** Verbindingsicoontjes met vier streepjes naast elke ping op het scorebord, gekleurd volgens kwaliteit, en een netwerkgrafiek die je onder de rondeklok kunt aanzetten: ping, pakketverlies en jitter, of een lopende grafiek van zes seconden met pieken in verlies in het rood. Als een gevecht verkeerd aanvoelt, zie je of het aan jouw verbinding lag, aan die van de ander of aan de server.
- **Met één klik meedoen.** Een link op de website of in Discord opent de launcher en zet je in de server, in het juiste team als de link dat aangeeft. Is de server vol, dan wacht de launcher op een vrije plek en doet hij vanzelf mee. Voor het verbinden doet hij een korte verbindingstest en zet hij extra pakketbescherming aan als je route pakketten verliest.
- **IPv6.** De launcher, het spel, de serverlijst en de dedicated server kunnen allemaal overweg met IPv6-adressen. Voor spelers die van hun provider geen volwaardig IPv4-adres meer krijgen, kan dat het verschil zijn tussen wel en niet kunnen hosten.
- **Een Verified-label.** Communityservers die de officiële build draaien, worden gemarkeerd in de serverbrowser en op de website.
- **Uitleg bij elke optie.** De launcher legt zijn eigen opties uit: houd de muisaanwijzer boven een grafische instelling en je leest wat ze doet en wat ze kost.
- **Eerlijker Ranked.** Een pinglimiet op Official #1, tijdelijke bans die op alle officiële servers gelden, en het volle ratingverlies als je een teammatch verlaat die je aan het verliezen bent.

## Discord: pick-ups en meldingen

Onze eigen Discord-bot is gebouwd en getest. Hij staat nog niet aan, omdat die stap de live servers raakt en op zijn eigen groen licht wacht.

- **Pick-ups.** Druk op Join queue. Als er twee volle teams wachten, krijgt iedereen een ready check van 60 seconden. De bot brengt de teams dan in evenwicht op skill rating door elke mogelijke verdeling te proberen, neemt een vrije matchserver, stelt een nieuw wachtwoord in, zet de competitieve wedstrijdmodus aan en stuurt elke speler een link waarmee hij in het juiste team terechtkomt. Na de match post hij de uitslag met de ratingwijziging van elke speler en start hij de volgende groep. Voor een community van onze grootte is dit matchmaking die werkt met twaalf mensen online.
- **Meldingen met bewijs.** Een `/report` in het spel komt in het staffkanaal terecht met de statistieken van de gemelde speler op die map en een verwijzing naar de juiste minuut in de opname die de server zelf van de match maakt. Een mens neemt altijd de beslissing.
- **Je account, gekoppeld.** Eén code die je in het spel typt, verbindt je Discord-account met je spelersprofiel. Geen wachtwoord en geen registratie. Vanaf dan toont `/profile` je rang, je rating en je laatste matches, en volgen je Discord-rollen je rang.
- **Live serverkaarten, evenementen en playtests.** Een kaart per officiële server die elke minuut bijgewerkt wordt, en inschrijvingen voor evenementen met herinneringen in je eigen tijdzone.

## Easy Anti-Cheat

De integratie van Easy Anti-Cheat zit in de engine en staat uit. Er rest één controle: een echte client die als beschermd bevestigd wordt wanneer hij via de echte anti-cheatlauncher gestart wordt. We kondigen het niet aan op basis van een build die er alleen juist uitziet. Het komt uit als die controle slaagt, en het krijgt een eigen post waarin staat wat het op je pc wel en niet ziet.

## DLSS 5

We krijgen er vragen over, dus hier is de eerlijke stand van zaken.

Platinum ondersteunt al DLSS-upscaling, DLAA, Frame Generation en Reflex. DLSS 5 is een ander soort technologie: in plaats van het beeld te verscherpen of frames toe te voegen, gebruikt het een neuraal netwerk om het afgewerkte beeld opnieuw te belichten en te verfijnen. Voor een spel met belichting uit deze periode is dat mogelijk de grootste visuele stap die er te zetten valt.

Ons plan is om het als een volwaardige, ingebouwde functie in de DirectX 12-renderer op te nemen. De renderer levert de bewegings- en diepte-informatie die zo'n techniek nodig heeft al zelf aan, dus er hoeft niets van buiten het spel aan vastgemaakt te worden.

Drie dingen liggen vast:

- Het wordt **optioneel en staat standaard uit**.
- Het staat **uit op Ranked**, en vijandelijke spelers worden overal van het effect uitgesloten. Een techniek die het beeld opnieuw schildert, mag nooit veranderen hoe zichtbaar een tegenstander is.
- Het komt alleen uit met **software die NVIDIA voor ontwikkelaars vrijgegeven heeft om te verspreiden**. Die is voor een project als het onze nog niet beschikbaar, en de timing hebben wij niet in handen.

Dus: gepland, onderzocht en niet beschikbaar. Je hebt er ook een grafische kaart voor nodig die het ondersteunt. We plakken geen datum op iets dat afhangt van een release die we niet zelf bepalen.

## Daarna

Verder weg, telkens met een eigen beslissing die nog genomen moet worden: meer maps uit de geschiedenis van TC:E, extra wapens en spelerskins uit andere TrueCombat-releases, eigen maps op communityservers met een veilige manier om ze te downloaden, en vrienden en party's in de launcher.

## Wat jij kunt doen

De volgorde hierboven komt rechtstreeks uit wat spelers ons na de playtests vertelden, en ze kan op dezelfde manier veranderen. Als iets hier voor jou zwaarder weegt dan de rest, of als er iets ontbreekt, laat het weten op [Discord](https://discord.gg/8kcHdg2Hch). De [roadmap](index.html#roadmap) volgt dit plan, en elk onderdeel krijgt een eigen devlogpost als het klaar is.
