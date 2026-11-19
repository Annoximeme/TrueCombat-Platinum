---
title: Hoor het gevecht
date: 2026-11-19
time: 03:20
summary: Elk wapen krijgt een eigen stem, inslagen krijgen twaalf variaties per oppervlak en de geluidsengine leert over kamers, deuropeningen en afstand. Plus free aim en AK's weer met twee handen. Het volledige verhaal van update 0.39.3.
image: img/devlog/front-lines-blast-courtyard.webp
tag: Update
kicker: Update 0.39.3
version: 0.39.3
---
In TrueCombat hoor je de meeste gevechten voordat je ze ziet. Een salvo achter een muur vertelt je waar de vijand zit, met hoeveel ze zijn en of ze binnen of buiten staan, en een goede speler maakt daar in een halve seconde een beslissing van. Dat werkt alleen als het geluid eerlijk is. Voor 0.39.3 zijn we alles nagegaan wat een wapen met je oren doet, van het moment dat de trekker breekt tot de laatste echo tegen een gebouw drie straten verder.

Twee dingen dreven het werk. Veel originele wapens deelden hetzelfde geluid of klonken dun naast alles wat we al verbeterd hadden, en de engine behandelde elk geluid alsof het gebeurde in de ruimte waar jij staat. 0.39.3 lost allebei op.

![Een schot in een binnenplaats op de Ultra-preset](img/devlog/front-lines-blast-courtyard.webp "Elk schot heeft nu een eigen stem en een echo die past bij waar het werd gelost. Ultra-preset, DirectX 12.")

## Elk wapen een eigen stem

We begonnen met naar elk wapenbestand in de game te luisteren, één voor één. Te veel pistolen en SMG's klonken bijna hetzelfde, en de meeste geweren misten de lage klap die een schot als een schot laat voelen.

De nieuwe set geeft elk wapen in de game een eigen bron:

- **35 wapens gebruiken een echte opname** van dat wapen of zijn naaste familielid. Geen twee wapens delen een opname, behalve tweelingen zoals akimbo-paren en vizierversies van hetzelfde geweer.
- **12 wapens houden hun originele TrueCombat:Elite-geluid, geremasterd**, waar geen opname duidelijk dat wapen was. Ze zijn opnieuw geknipt, kregen een klap en zijn verdeeld over vier licht verschillende takes, zodat volautomatisch vuur niet als een loop klinkt.
- **Elk schot heeft een klap**: een korte lage dreun afgestemd op het kaliber, onder een donkerder lichaam. Je eigen wapen krijgt er meer van dan dat van andere spelers, want zo klinkt het als het tegen je schouder zit.
- **Het is luider**, maar niet oneerlijk. Wapens van andere spelers zitten ongeveer 3 dB boven het origineel en je eigen wapen ongeveer 7 dB, allebei begrensd voordat het vervorming wordt. Hoe ver een schot draagt en hoe het met afstand afneemt is niet veranderd, dus niemand hoort verder dan voorheen.

Niet iedereen wil een nieuw geluid voor een game die je al twintig jaar speelt. Options > Audio heeft nu **Weapon sounds: Remastered / Original**. Original speelt precies wat 0.39.2 speelde. Beide sets laden met de map, dus wisselen gaat meteen, zelfs midden in een ronde.

## Een echo die weet waar je bent

Een geweer in een kleine kamer, een lange hal, een open straat en een sneeuwvlakte horen niet dezelfde naklank te hebben. Elk schot krijgt nu een naklank voor de ruimte waarin het valt (kamer, hal, buiten of sneeuw) en voor zijn wapenklasse (pistool en SMG, geweer, of DMR, sniper en shotgun), met twee takes van elk zodat herhaalde schoten niet gekopieerd klinken.

![Een steegje op Harbour op de Ultra-preset](img/devlog/front-lines-harbour-cqb-alley.webp "Steegjes en binnenplaatsen kaatsen schoten nu terug van hun muren. Harbour, Ultra-preset.")

## Inslagen die bij de originelen passen

Inslagen waren een ander probleem. De originele TC:E-inslagen zijn kort en droog, en spelers kennen ze uit het hoofd. Ze vervangen zou de game vreemd laten voelen, dus we hielden ze en voegden er meer omheen toe.

- Elk oppervlak (vlees, metaal, plaatstaal, hekken, hout, glas, steen en gebladerte) houdt zijn vijf originele geluiden en krijgt er **zeven nieuwe** bij, dus het kiest nu uit twaalf. Hetzelfde geluid speelt nooit twee keer na elkaar.
- Elke nieuwe variatie is afgestemd op de originelen van zijn set: dezelfde klankbalans, hetzelfde niveau binnen 1,5 dB, dezelfde lengte. Lang nagalmende sets zoals metaal dragen een stukje van de originele galm onder de nieuwe inslag. Sommige zijn echt opgenomen inslagen, sommige mengen de eerste milliseconden van een origineel met een opgenomen lichaam, en sommige zijn de originelen opnieuw gestemd.
- **Aarde, zand, sneeuw en gras waren stil** in TC:E. Ze krijgen nu twaalf zachte inslagen van zichzelf.
- **Ricochetten** fluiten weg van harde oppervlakken.
- **Rakelingse knallen en gefluit** gaan van vier variaties naar twaalf.

## Een geluidsengine die kamers begrijpt

De grootste verandering zit onder de motorkap. Zeven verbeteringen aan de geluidsengine veranderen hoe elk geluid je bereikt, niet alleen geweervuur.

![Gestapelde kratten in het magazijn op Snow](img/devlog/front-lines-snow-warehouse.webp "Een vuurgevecht in een magazijn dreunt nu in dat magazijn, ook als je buiten staat. Snow, Ultra-preset.")

### De ruimte van de schutter

Tot nu toe gebruikte elk geluid één galm: die van de ruimte waar jij staat. Een geweer dat in een grote schuur werd afgevuurd terwijl jij op straat stond, klonk alsof het op straat werd afgevuurd. Nu galmen geweervuur en ontploffingen verderop ook in **de ruimte waar ze werden afgevuurd**. De engine tast de ruimte rond de schutter af, stemt er een galm op af en stuurt het schot erin, gedempt door dezelfde muren waar het schot doorheen gaat. Een gevecht in een magazijn dreunt als een magazijn, en je hoort het verschil met een gevecht in de open lucht.

### Door de deuropening

Stond er een muur tussen jou en een geluid, dan dempte de engine het zwaar en liet het waar het was. Nu zoekt hij de opening waar het geluid echt doorheen zou gaan en test daarvoor 32 punten rond jou en de bron op een vrije weg. Vindt hij er een, dan hoor je het geluid **uit de deur of het raam**, op de lengte van die weg en maar licht gedempt. Sta je in een huis met één deur, dan komt een schot buiten binnen via de deur, niet door de muur.

### Het luidste schot blijft helder

Een groot vuurgevecht werd vroeger een muur van lawaai. Nu leidt het luidste verse schot of de luidste ontploffing de mix even, en ander geweervuur, inslagen, puin en hulzen die meer dan 12 dB zachter zijn, gaan tot 4 dB terug. Voetstappen, rakelingse knallen, voicechat en menu's worden nooit aangeraakt, dus niets waarmee je een vijand vindt wordt zachter.

### Afstand kost tijd

Geluid reist met ongeveer 343 meter per seconde, en nu ook in de game. Geweervuur en ontploffingen verderop beginnen een moment later: ongeveer 0,3 seconden voor een schot op 100 meter. **Het is voor elke speler hetzelfde** en kan niet uitgezet worden voor een voordeel. Dichtbij krijgen schoten bij muren één of twee korte **muurslagen**, de harde weerkaatsing die je hoort als je in een steeg vuurt. In een open veld zijn er geen.

![De kade van Harbour op de Ultra-preset](img/devlog/front-lines-harbour-water-fire.webp "In de open lucht zijn er geen muurslagen, en verre schoten komen een moment na de flits aan. Harbour, Ultra-preset.")

### Meer stemmen, fijner geluid

De engine kan nu **240 geluiden tegelijk** spelen in plaats van 192, en mixt op 48 kHz. Zijn alle stemmen bezet, dan laat hij het geluid vallen dat je op dat moment het minst hoort in plaats van het oudste, zodat een groot gevecht het schot naast je niet afkapt.

### Je oren reageren

Een schot zonder demper vlak bij je, door iemand anders, dempt je gehoor even met een zwakke piep, die in ongeveer twee seconden terugkomt. Je eigen schoten tellen nooit mee. Het is milder dan een ontploffing dichtbij, en de bestaande opties voor ontploffingsdemping en tinnitus zetten het uit.

### Voetstappen in hun ruimte

Voetstappen verderop galmen nu in de ruimte waar de loper is, net als geweervuur. Alleen de galm is nieuw. Hoe luid voetstappen zijn, hoe ver ze dragen en hoe muren ze tegenhouden is precies zoals voorheen, dus niemand krijgt luidere of zachtere stappen dan in 0.39.2.

## Free aim, eindelijk goed gedaan

Free aim zat al verborgen in de game: een kopie van de free aim tijdens het richten uit TC:E, sinds 0.38.0, uit en alleen actief tijdens het richten. 0.39.3 maakt er een echte optie van onder **Options > Mouse & View > Free aim**, **standaard uit**:

- **Deadzone**: vanuit de heup beweegt je muis het wapen binnen een klein vak (ongeveer 4 graden links en rechts, 2,5 omhoog en omlaag) voordat het beeld draait.
- **Wide deadzone**: hetzelfde met een groter vak.
- **Classic (aim only)**: de originele free aim van TC:E, ongewijzigd.

Richt je over het vizier in een deadzone-modus, dan glijdt het vizier in ongeveer een tiende seconde naar waar het wapen wijst terwijl het beeld meedraait, zodat je je doel nooit kwijtraakt. Schoten vertrekken altijd langs het wapen, de server is het eens met je scherm, en er komt geen invoervertraging bij. We testten het met 320.000 willekeurige muisbewegingen op vier verschillende framerates, om zeker te zijn dat het wapen altijd precies wijst waar je het heen bewoog.

## Weer twee handen aan de AK

Een tijdlang hielden andere spelers hun AK-47 en G3 in third person met één hand vast. Eén regel in het animatiescript was te lang en werd afgekapt, waardoor die geweren terugvielen op een houding met één hand. Die regel is gerepareerd, en beide handen zitten weer aan het wapen.

![Een AK-47 op Railhouse](img/devlog/cqb-ak47-railhouse-ultra.webp "De AK-47 op Railhouse. Ultra-preset.")

## Hoe we het testten

Geluid is moeilijk te testen met een machine. Wat gemeten kon worden, is gemeten. Elke nieuwe inslag is vergeleken met zijn originelen op niveau en klankbalans. De engine meldt hoeveel ruimtes hij afstemde, hoeveel wegen door deuropeningen hij vond en hoe vaak hij geluiden liet terugtreden, en die tellingen controleerden we met acht bots die vochten op Village. Elke verbetering heeft een eigen schakelaar, dus we vergeleken de game met elke verbetering aan en uit. Daarbovenop kwamen de volledige releasetest van 19 gevallen, botwedstrijden op zes maps, en een vergelijking van CPU en frametijd met 0.39.2, want 240 stemmen en extra galm zijn niet gratis.

Wat een machine ons niet kan vertellen, is of het goed klinkt. Dat deel ligt bij jou. Klinkt een wapen verkeerd, galmt een ruimte vreemd of stuurt een deuropening een geluid de verkeerde kant op, laat het ons weten op [Discord](https://discord.gg/7Dg4yhhvGF) met de map en waar je stond.

> Liever het oude geluid? Options > Audio > Weapon sounds > Original brengt het TC:E-geweervuur terug. De andere verbeteringen aan de geluidsengine blijven aan en gelden voor iedereen op dezelfde manier.

## Wat volgt

Hierna komt het licht. Donkerdere maps met echt licht en schaduw worden nu getest, en ze komen in een volgende update zodra we tevreden zijn over hoe elke map eruitziet. Daarna is de interface-vernieuwing van 0.40.0 onderweg. Zoals altijd: bedankt voor het spelen, en voor het luisteren.
