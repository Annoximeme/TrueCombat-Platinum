---
title: Aan het front
date: 2026-11-18
summary: Bots die luisteren, plannen en samen terugnemen, vier klassieke community-maps, een volledig vernieuwde launcher met vrienden, en een nieuwe laag licht, weer, geluid en lichaamstaal op elke map. Het volledige verhaal van update 0.39.0.
image: img/devlog/front-lines-teaser-clean.webp
tag: Update
kicker: Update 0.39.0
version: 0.39.0
---
![Key art voor update 0.39.0: Front Lines](img/devlog/front-lines-teaser.webp "Update 0.39.0: Front Lines. Stadtrand, Ultra-preset, DirectX 12.")

De meeste updates voegen dingen toe waar je naar kunt wijzen. 0.39.0 gaat vooral over de momenten tussen de schoten: het geschuifel van iemand die achter een muur van positie wisselt, licht dat op Snow door een deuropening breekt, een verdedigend team dat op elkaar wacht voor het een site terugneemt in plaats van één voor één te sneuvelen. Dat zijn de momenten die TrueCombat:Elite twintig jaar geleden zo spannend maakten, en precies die momenten wilden we dieper maken.

Het is ook een van onze grootste updates tot nu toe. Dertien afzonderlijke stukken werk zitten in deze release, van de manier waarop bots denken tot de manier waarop een gevallen soldaat op een trap tot rust komt, naast een launcher die van de grond af opnieuw is gebouwd en vier community-maps waar velen van jullie al naar vragen sinds Platinum begon. Dit is de lange versie van het verhaal: alles wat we veranderd hebben, en waarom.

## Tegenstanders die nadenken

Bots zitten al sinds het begin in Platinum, en lang was hun taak eenvoudig: vind een vijand, schiet, zoek de volgende. Om op te warmen werkt dat. Als een match voelt het niet. Voor 0.39.0 hebben we opnieuw opgebouwd hoe bots een ronde waarnemen, hoe ze beslissen wat ze doen en hoe ze als team samenwerken.

### Ze luisteren nu

Voetstappen en geweervuur dragen nu informatie. Een bot die je aan de andere kant van een muur hoort lopen, weet ongeveer waar je bent, ook zonder je te zien, en handelt ernaar: hij draait naar het geluid, houdt een hoek vast of verplaatst zich om je af te snijden. Verliest een bot je uit het oog, dan vergeet hij je niet meer. Hij onthoudt waar je het laatst gezien werd en speelt rond die plek, en controleert de hoek waarachter je verdween in plaats van er voorbij te lopen.

Lopen, hurken en kiezen wanneer je geluid maakt, tellen tegen bots dus net zo goed als tegen mensen. Sprint over een open binnenplaats op Village en de verdedigers weten het.

### Bomrondes die spelen als een match

Bommodus kreeg de meeste aandacht. Aan het begin van elke ronde spreekt het aanvallende team een plan af: welke site, welke route en wie als eerste gaat. Aanvallers bewegen als groep, kunnen hun weg naar binnen met rook afdekken en verspreiden zich rond de lading zodra die ligt, zodat één verdediger ze niet meer één voor één kan uitschakelen terwijl ze door dezelfde deur lopen.

Verdedigers houden hun sites in plaats van rond te dwalen. Zijn ze in de minderheid, dan trekken ze terug, en zodra de bom ligt, verzamelen ze en nemen ze samen terug. Die ene verandering maakte het grootste verschil in onze testmatches. Aanvallende bots wonnen vroeger bijna drie op de vier rondes, vooral omdat verdedigers één voor één aankwamen. Met verdedigers die zich hergroeperen, zijn bomrondes tegen bots nu bijna gelijk opgaand.

![Bots vallen samen een bomsite aan op Snow](img/devlog/front-lines-bots-snow-push.webp "Aanvallers trekken samen een site op, op Snow.")

![Verdedigers rukken op om een site terug te nemen op Snow](img/devlog/front-lines-bots-snow-retake.webp "Verdedigers verzamelen en rukken samen op om de site terug te nemen.")

### Beslissingen in plaats van reflexen

In een gevecht wegen bots nu af of ze blijven staan, opdringen of terugvallen, op basis van hun gezondheid, hoeveel teamgenoten in de buurt zijn en hoe de ronde loopt. Ze variëren hun peeks in plaats van telkens op dezelfde hoogte uit dezelfde hoek te komen, en soms wachten ze tot jij de eerste zet doet.

Elk team houdt ook bij welke rondeplannen op welke map gewerkt hebben en past zich tijdens een sessie aan. Mislukt een route op Stadtrand keer op keer, dan proberen de bots de volgende rondes iets anders. Speel een lange sessie tegen ze en je merkt dat ze niet meer in dezelfde truc trappen.

![Een bot stormt door een zijstraat op Village](img/devlog/front-lines-bots-village.webp "De laatste kill van een ronde op Village, in de ronde-replay.")

### Vlottere rondes

Sommigen van jullie merkten een korte hapering op het einde van rondes op servers met bots. We hebben die herleid tot het moment waarop bots hun routes voor de volgende ronde herberekenen, en dat werk wordt nu gespreid zodat de server niet meer stokt. Servers met bots zouden van ronde tot ronde vlotter moeten aanvoelen.

### Uit de weg

Bots kregen ook een reeks navigatiefixes. Ze klimmen niet meer steeds opnieuw op dezelfde richel, en een bomdrager blijft bij één site in plaats van heen en weer te wisselen. Een bot die vastloopt aan het begin van zijn route, of ergens belandt zonder route, zoals op een dak of in de put bij de ladder op Railhouse, vindt nu zelf de weg terug. Eén bot houdt de taak om te ontmantelen of de bom op te rapen, in plaats van twee bots die ze steeds overnemen, en bots staan niet meer in je wanneer je stilstaat op de plek waar ze naartoe wilden. Dicht bij een bekende vijand lopen ze stil, en rondestarts met een volle server bots verlopen vlotter.

Eén fix zullen velen meteen merken: bots bevriezen niet meer voor je neus terwijl je door een scope richt. Kunnen ze niet uit je schootslijn, dan bukken ze en blijven ze bewegen. En bots met een sluipschuttersgeweer gebruiken nu op elke moeilijkheidsgraad de scope.

## Vier klassiekers keren terug

Villa 2.1, Shozen, Snowtown en Chlite hoorden bij de meest gespeelde community-maps uit de TrueCombat:Elite-jaren, en het zijn de maps waar ons het meest naar gevraagd werd toen Platinum begon. Alle vier zitten ze nu in het spel, dus elke server kan ze draaien en je kunt ze offline tegen bots spelen.

We lieten de maps precies zoals hun makers ze gemaakt hebben: dezelfde indeling, dezelfde texturen en dezelfde plekken die je je herinnert. Wat we wel veranderd hebben, is het geluid. Een aantal originele geluiden was in lage kwaliteit opgenomen of speelde veel te luid naast de eigen sfeergeluiden van Platinum. We hebben ze opgeschoond, op hetzelfde niveau gebracht als de rest van het spel en een paar weggelaten die we niet mochten meeleveren. Beide bomsites op Villa en Chlite werken nu zoals hun makers het bedoelden, en de krat bij site A op Villa 2.1 breekt nu wanneer de bom ontploft.

De vier maps krijgen ook alles wat de kernmaps hebben: een minimap, een tactische kaart en een laadscherm met plattegrond, afbeelding en beschrijving. Op Villa 2.1 rapen bots nu de vlag op in Flag Capture.

![Tactische kaart van Snowtown](img/devlog/front-lines-snowtown-tacmap.webp "De tactische kaart op Snowtown: de volledige plattegrond, beide bomsites en de eigen plaatsnamen van de map.")

![Tactische kaart van Chlite](img/devlog/front-lines-chlite-tacmap.webp "Ook Chlite krijgt zijn plattegrond, sites en callouts.")

![Minimap op Snowtown](img/devlog/front-lines-snowtown-minimap.webp "De minimap volgt je door Snowtown, en callouts zoals North St. tonen waar de bom gevallen is.")

De plattegronden komen uit de maps zelf: we volgden elke vloer die een speler vanaf de spawns kan bereiken en tekenden het bovenaanzicht in dezelfde stijl als de kernmaps, zodat een callout op Snowtown voor iedereen in het team hetzelfde betekent.

![Bom ontploft bij site A op Villa 2.1](img/devlog/front-lines-villa-site-a-blast.webp "Site A op Villa 2.1: de lading gaat af, de krat breekt en de ronde gaat naar de Terrorists.")

![Villa 2.1](img/devlog/front-lines-villa.webp "Villa 2.1 's avonds, Ultra-preset, DirectX 12.")

![Snowtown](img/devlog/front-lines-snowtown.webp "Snowtown, Ultra-preset, DirectX 12.")

![Shozen](img/devlog/front-lines-shozen.webp "Shozen, Ultra-preset, DirectX 12.")

![Chlite](img/devlog/front-lines-chlite.webp "Chlite, Ultra-preset, DirectX 12.")

De vier community-maps draaien op Unranked-servers. Ranked blijft voorlopig bij de vaste mappool, zodat elke ranked match gespeeld wordt op maps die daarvoor in balans zijn gebracht.

### Stadtrand krijgt zijn tweede site terug

Toen we de bomsites op de community-maps herstelden, ontdekten we dat hetzelfde probleem stilletjes site A op Stadtrand had uitgeschakeld. Vanaf 0.39.0 werken beide sites weer, op elke server, ook op Ranked. Stadtrand speelt voor het eerst in heel lange tijd weer als een map met twee sites.

![Stadtrand met beide bomsites op de HUD](img/devlog/front-lines-stadtrand-bomb-hud.webp "Stadtrand: sites A en B weer allebei op de HUD.")

## Licht, weer en water

Het tweede grote thema van 0.39.0 is sfeer. Geen van deze veranderingen verandert hoe een vuurgevecht verloopt, maar samen maken ze van de maps echte plekken op een echt moment van de dag.

### Zachter licht

De gebakken belichting is gladder, met zachte randen waar schaduwen over muren en vloeren vallen in plaats van de harde trapjes van de originele lightmaps. Het verschil zie je het best op vlakke muren in de middagzon.

![Belichting voor](img/devlog/front-lines-lightmap-before.webp "Voor: de originele gebakken schaduwen op Village.")

![Belichting na](img/devlog/front-lines-lightmap-after.webp "Na: dezelfde hoek met gladdere belichting in 0.39.0.")

### Wind, zon en natte grond

Bomen, struiken, gras en zeildoek wiegen nu zachtjes in de wind, terwijl stammen en muren stil blijven staan. Op DirectX 12 breekt zonlicht als zachte stralen door openingen in de omgeving, en kijken naar de zon geeft een lichte schittering. Natte plekken op de grond weerspiegelen de wereld rondom op de Ultra-preset, en baksteen, kasseien en puin krijgen van dichtbij echte diepte: voegen zakken weg in het oppervlak wanneer je langs een muur kijkt.

![Bomen in de wind op Village](img/devlog/front-lines-wind-tree.webp "Village: takken en bladeren bewegen mee met de wind, de stam blijft staan.")

![Gras en struiken in de wind op Village](img/devlog/front-lines-wind-grass.webp "Gras en struiken langs het tuinpad op Village wiegen zachtjes.")

![Natte grond weerspiegelt de haven op Harbour](img/devlog/front-lines-harbour-wet.webp "Natte plekken vangen weerspiegelingen op Harbour, DirectX 12 Ultra.")

### Echte diepte op baksteen en steen

De diepte op baksteen, kasseien, grind en rots verdient een eigen vermelding, want die hebben we laat in de tests opnieuw gebouwd. De eerste versie schatte hoe diep een oppervlak moest zijn op basis van hoe donker de textuur was, waardoor een vlek op een muur een gat werd en lange bakstenen muren in een gekartelde zaagtand braken wanneer je erlangs keek. Dat wilden we niet uitbrengen. Elk van deze oppervlakken heeft nu een echte hoogtekaart, gebouwd uit dezelfde normal maps die het belichten, zodat de diepte klopt met het licht: voegen en afgebrokkelde randen zakken weg, de bakstenen zelf blijven staan. Het effect verdwijnt onder scherpe hoeken en op oppervlakken die naar beneden kijken, pleister en plafonds krijgen het nooit, en op Ultra kost het ruim minder dan een milliseconde, zelfs wanneer een muur je hele scherm vult.

![Bakstenen muur met hoogtekaarten op Railhouse](img/devlog/front-lines-brick-depth.webp "Railhouse, DirectX 12 Ultra: echte diepte op de baksteen, met verzonken voegen en strakke randen langs de hele muur.")

![Bakstenen muur van dichtbij op Railhouse](img/devlog/front-lines-brick-depth-close.webp "Van dichtbij: elke baksteen steekt uit boven de voeg, en de randen blijven strak onder een kleine hoek.")

### Een stemming per map

Elke map krijgt ook een eigen subtiele kleurstemming. Snow is iets kouder, Delta iets warmer. Het is bewust ingetogen: het doel is een gevoel van plaats, geen filter.

!compare(img/devlog/front-lines-mood-delta-off.webp | Zonder | img/devlog/front-lines-mood-delta.webp | Kleurstemming | Delta: de kleurstemming geeft het stoffige plein wat warmte zonder te veranderen wat je ziet.)

!compare(img/devlog/front-lines-mood-snow-off.webp | Zonder | img/devlog/front-lines-mood-snow.webp | Kleurstemming | Snow: een iets koeler, helderder beeld.)

### Water, vuur en rook

Water rimpelt nu wanneer spelers erdoor waden en wanneer kogels het oppervlak raken. Kom boven na een zwempartij en er lopen een paar seconden druppels langs de randen van je beeld. Vuur en explosies zijn veel gedetailleerder, en rook licht kort op bij elke ontploffing en elke mondingsvlam, zodat een vuurgevecht in een rookgordijn nu van binnenuit oranje gloeit.

### Rijp op Snow

Op Snow vormt zich langzaam rijp aan de randen van je beeld zolang je buiten bent, en die smelt weg wanneer je binnenstapt. Het blijft aan de randen van het scherm, nooit in het midden waar je mikt.

![Rijp aan de randen van het beeld op Snow](img/devlog/front-lines-lens-frost.webp "Buiten op Snow vormt zich rijp aan de randen van je beeld.")

![Rijp in een steegje op Snow](img/devlog/front-lines-lens-frost-alley.webp "Rijp omlijst het beeld in een steegje op Snow en trekt weer weg zodra je naar binnen gaat.")

### Gelijke kansen op Ranked

Sfeer mag nooit een ranked match beslissen. Op Ranked-servers en in clanmatches staan zonnestralen, schittering, kleurstemming, rijp en oplichtende rook uit, zodat elke speler hetzelfde beeld ziet, ongeacht zijn instellingen. Wind, zachter licht, rimpelingen en de detailverbeteringen blijven overal aan, omdat ze niet beïnvloeden wat je kunt zien.

## Dichter bij de soldaat

Het derde thema is de soldaat die je speelt en de soldaten die je ziet. TrueCombat draaide altijd om weloverwogen, geloofwaardige gevechten, en er ontbraken veel kleine dingen die een lichaam echt doen aanvoelen.

### Geluid dat je meedraagt

Je uitrusting maakt nu geluid terwijl je beweegt: een zacht geritsel bij elke stap, luider als je loopt, en een rammelend magazijn als je sprint. De laatste kogel in een magazijn eindigt met een droge klik, zodat je weet dat je leeg bent voor je naar de teller kijkt. Al deze geluiden zijn gemaakt uit opnames die al in het spel zitten, zodat ze natuurlijk passen bij de originele wapens.

### Weinig gezondheid en vermoeidheid

Zak onder een kwart van je gezondheid en er zet een trage hartslag in. Die versnelt naarmate je dichter bij de dood komt, het geluid wordt doffer en de kleur trekt weg uit de wereld. Na een lange sprint kom je een paar seconden op adem. Niets hiervan verandert je mikken of bewegen: het vertelt je hoe het met je gaat zonder nog een getal op het scherm.

### Uitrusting die je ziet

Wat je draagt, zit nu zichtbaar op je lichaam. Je pistool hangt aan je rechterdij, je mes ligt plat op je linkerheup en je granaten hangen aan je riem. Samen met het geweer op je rug, dat in 0.34.0 kwam, kan een vijand je uitrusting nu in één oogopslag lezen.

![Geweer op de rug en granaten aan de riem](img/devlog/front-lines-holster-rifle-back.webp "Geweer op de rug, granaten aan de riem, pistool op de dij.")

![Pistool in de holster op de dij met een geweer in de hand](img/devlog/front-lines-holster-pistol-thigh.webp "Met een geweer in de hand hangt het pistool aan de rechterdij.")

### Handen waar ze horen

Deze gaat terug tot het originele spel. In de third-person-animaties van TrueCombat:Elite hield de steunhand het geweer nooit echt vast: hij zweefde naast of onder de loop, in elke houding en bij elk tweehandig wapen. We hebben de arm opnieuw opgebouwd in elf reeksen geweeranimaties, van staan tot gehurkt lopen en vuren, zodat de linkerhand nu op de handbescherming rust, met een kleine aanpassing per wapen. De Shorty-shotgun wordt nu met één hand vastgehouden, zoals het hoort. First person blijft ongewijzigd.

![Third-person-greep voor](img/devlog/front-lines-grip-before.webp "Voor: de steunhand zweeft naast de AK-47.")

![Third-person-greep na](img/devlog/front-lines-grip-after.webp "Na: de steunhand houdt de handbescherming vast.")

### Hoe soldaten vallen

Gevallen soldaten komen nu natuurlijk tot rust. Een lichaam dat tegen een muur sterft, valt ervan weg in plaats van erdoorheen. Een soldaat die al lopend geraakt wordt, behoudt een beetje vaart en schuift nog een stukje door voor hij stilligt. Op hellingen en trappen liggen lichamen langs de grond in plaats van erboven te zweven, en armen, benen en hoofd komen te rusten op wat eronder ligt. Een klein detail, tot je voor het eerst een lichaam over een trap in Railhouse ziet hangen.

### Een teamgenoot volgen

Wanneer je na je dood een teamgenoot volgt, beweegt zijn wapen nu zoals in zijn eigen beeld. Je ziet hem sprinten met het wapen omlaag, zijn vizier opbrengen, zwaaien en deinen terwijl hij beweegt. Een goede speler volgen is nu veel leesbaarder.

## Focuszoom

Voor schutters komt er een nieuwe laag bij het mikken. Terwijl je door je vizier kijkt, houd je de rechtermuisknop ingedrukt om je beeld te stabiliseren met een lichte extra zoom; laat los en je bent terug bij je normale vizierbeeld. Gebruik je hold-to-aim, dan focust de sprinttoets terwijl je mikt.

Focuszoom is puur een zoom: wapenzwaai, spreiding, terugslag en beweging blijven precies hetzelfde als zonder. Het werkt op elke server met 0.39.0, ook op Ranked.

!compare(img/devlog/front-lines-focus-zoom-off.webp | Gericht | img/devlog/front-lines-focus-zoom.webp | Focuszoom | Village: het normale vizierbeeld, en hetzelfde beeld met focuszoom ingehouden.)

## Geluid dat standhoudt

Op audioapparaten die op hoge samplefrequenties staan, 96 kHz en hoger, kon het geluid enkele seconden na de start van een match wegvallen of veranderen in doffe bonken. 0.39.0 levert een nieuwere versie van de audiobibliotheek die het spel gebruikt, en we hebben die getest op elke gangbare frequentie tot 384 kHz. Zette je je headset op 48 kHz om Platinum te kunnen spelen, dan mag hij terug.

De havensfeer van Northport speelt weer. De map vraagt er altijd al om, maar het geluid zelf ontbrak in de originele release, waardoor de haven bijna twintig jaar stil is gebleven. We hebben ook een ongebruikt systeemgeluid vervangen dat met de originele spelbestanden werd meegeleverd.

## Launcher 3.0

De launcher is van de grond af opnieuw gebouwd, en omdat iedereen hem als eerste ziet, hebben we er onze tijd voor genomen.

De Play-pagina toont nu live serverkaarten met de huidige map, spelers en ping, en Play zegt altijd waar het je naartoe brengt. De serverbrowser krijgt tabbladen voor favorieten, recente servers, vrienden en LAN, een zoekbalk, spelersbalken en een zijpaneel met de volledige spelerslijst, en kan een volle server joinen zodra er een plek vrijkomt. Nieuws opent als volledige artikels met afbeeldingen.

![De nieuwe Play-pagina in Launcher 3.0](img/devlog/front-lines-launcher-play-nl.webp "De nieuwe Play-pagina: live servers, nieuws en snel spelen op één plek.")

### Vrienden

Met Vrienden voeg je elkaar toe met een vriendencode, zie je wie er speelt en op welke server, nodig je elkaar uit en join je met één klik. Het is volledig optioneel: het staat uit tot je het aanzet, je kiest zelf wat anderen kunnen zien, en wie het uitzet, wist zijn vriendengegevens.

![Vrienden in Launcher 3.0](img/devlog/front-lines-launcher-friends-nl.webp "Vrienden: voeg elkaar toe met een code, zie wie er speelt, join met één klik.")

### De details

Het trayicoon heeft een donker menu met snel spelen, de schietbaan en instellingen, en meldingen dragen nu het icoon van het spel. Een downloadpaneel toont voortgang en snelheid en laat je pauzeren en hervatten, en een hervatte update downloadt afgewerkte bestanden nooit opnieuw. De instellingen krijgen een zoekvak, een grafische preview die je kunt verslepen om presets te vergelijken en een nieuw tabblad Toegankelijkheid met hoog contrast, grotere tekst, kleurenblindvriendelijke markeringen en minder beweging. Schermlezers kunnen de pagina's, rijen en knoppen van de launcher nu voorlezen. De launcher is ook beschikbaar in het Nederlands, naast Engels, Duits, Frans en Pools.

Launcher 3.0 bevat ook het herstelwerk uit launcher 2.6.2: ontbrekende of beschadigde spelbestanden worden automatisch opnieuw gedownload, en als er iets misgaat, vertelt de foutmelding nu wat er gebeurd is.

## Een duidelijkere HUD

We zijn elke spelmodus scherm per scherm doorgegaan en hebben weggewerkt wat in de weg zat. Mapnamen staan nu leesbaar op het scorebord en de tactische kaart, rondeuitslagen noemen de teams ("Terrorists win the round"), en de doelkaarten van Bomb, Flag en Capture Point zeggen wat je nu moet doen. In Capture Point staat het punt op de tactische kaart en de minimap, en in Team Deathmatch en Flag ziet een speler die op de volgende golf wacht wanneer hij weer inzet, in plaats van te lezen dat er geen inzet meer is.

Kleine dingen tellen ook: toeschouwers van teamwedstrijden krijgen het teamscorebord, het paneel van de schietbaan en de FPS-teller staan niet meer op de minimap, kleine UI-formaten houden alle tekst leesbaar, het podium op het einde van een wedstrijd is op elke map even goed belicht, en de killfeed, het chatvak, het stemmenu en de melding om een wapen op te rapen overlappen of knippen geen tekst meer af. Flitsgranaten verblinden nu ook de minimap, het kompas en de doelkaart, en de replaycamera van de laatste kill belandt niet meer in de schutter of achter een hek.

![Doelkaart in Bomb](img/devlog/front-lines-hud-bomb-card.webp "Bomb op Railhouse: de doelkaart vertelt de bomdrager precies wat hij nu moet doen.")

![Capture Point-kaart](img/devlog/front-lines-hud-capture-point.webp "Capture Point: de kaart toont wie er verovert en hoe ver, en het punt staat op de minimap.")

## Close quarters

CQB blijft experimenteel terwijl we het op het niveau van het kernspel brengen. In 0.39.0 gelden de spawnregels van CQB alleen nog in de CQB Rules-playlist, zodat elke andere modus standaard-spawns houdt, ook met experimentele content aan. In CQB Rules worden gezondheidsherstel en de perks Protected en Tank niet meer ongedaan gemaakt door de volgende treffer.

Vanaf deze update draait Official #2 (Unranked) met experimentele content aan: de nieuwe CQB-wapens zitten daar in elke match, en Harbour komt in de rotatie als Team Deathmatch.

![CQB-steegje op Harbour](img/devlog/front-lines-harbour-cqb-alley.webp "Harbour na de regen: natte kasseien, nauwe steegjes en het CQB-arsenaal, DirectX 12 Ultra.")

![CQB-binnenplaats op Harbour](img/devlog/front-lines-harbour-cqb-run.webp "Een bot dringt door de overwoekerde binnenplaats op Harbour.")

## Fixes

- Bomrondes worden niet meer dubbel geteld wanneer de explosie iemand meeneemt.
- De explosie van de bom raakt nu iedereen in de buurt en telt voor de speler die hem plaatste.
- SpecOps kunnen geen opgeraapte bom meer plaatsen.
- Geblokkeerde draaideuren zwaaien op servers niet meer achteruit.
- Granaten en rook uit de vorige ronde worden opgeruimd wanneer een nieuwe ronde begint.
- Spelers glijden niet meer van hellingen terwijl ze stilstaan, en blijven staan wanneer ze bergaf lopen.
- Het trekken van de pin van een granaat is nu hoorbaar, voor jou en voor spelers in de buurt.
- Vlotter bewegen langs de glazen gevels op Railhouse, en minder korte haperingen de eerste keer dat een geluid of effect gebruikt wordt.
- Er verschijnt een melding "Verbinding onderbroken" wanneer de server niet meer antwoordt.
- Opgenomen demo's spelen af zonder dat er menu's over openen.
- Het vizier van de M4 SOPMOD toont in 1440p en 4K één rode stip.
- Bugmeldingen (F12) in hoge resoluties zeggen niet meer dat de screenshot te groot is om te uploaden.
- Het Deployment-menu sluit wanneer de wedstrijd afloopt.
- We hebben onze beveiligingsmaatregelen aangescherpt en uitgebreid.

## Hoe we het getest hebben

Elke kandidaat-build van 0.39.0 ging door onze volledige regressietest: negentien geautomatiseerde scenario's met matches tegen bots, netwerkspel, serverinstellingen, herstarts en predictie, op zowel DirectX 12 als OpenGL. Daarbovenop hebben we het zelf gespeeld, de anti-cheat van begin tot eind gecontroleerd en de nieuwe launcher door een volledige update en herstelling vanaf 0.38.2 gehaald. Onderweg kwamen er een paar problemen boven, van een bomronde die dubbel telde tot deuren die de verkeerde kant op zwaaiden, en die zijn allemaal opgelost in de build die uitkomt.

## Wat komt er hierna

0.39.0 is de laatste grote update voor 0.40, onze grootste mijlpaal tot nu toe. Een deel van wat eraan komt, lieten we al zien in [Opnieuw gemodelleerd, op weg naar 0.40](devlog-remodelled.html), en er is nog veel meer dat we nog niet getoond hebben.

Terwijl je dit leest, gaat 0.39.0 door zijn laatste controles, en heel binnenkort komt hij binnen via de launcher. De volledige patch notes staan op de releasepagina zodra hij uitkomt. Start dan Snow op en luister. Tot aan het front.
