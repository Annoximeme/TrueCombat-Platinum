---
title: Opnieuw gemodelleerd, op weg naar 0.40
date: 2026-11-17
time: 21:30
summary: We bouwen TrueCombat: Platinum van binnenuit opnieuw op, model per model. Een eerste blik op de nieuwe wapenmodellen, de vernieuwde interface en het lichtwerk voor 0.40, met elke voor-en-na die we tot nu toe hebben.
image: img/devlog/models-teaser-clean.webp
tag: Graphics
kicker: Op weg naar 0.40
---
![Op weg naar 0.40: Remodelled](img/devlog/models-teaser.webp "Het nieuwe P19-pistool, een van de eerste modellen die we volledig opnieuw hebben gebouwd.")

Het meeste van wat je vandaag in Platinum ziet, stamt nog uit 2006. De maps, de wapens en de spelermodellen zijn gemaakt voor de hardware van toen, en lange tijd bestond ons werk vooral uit ze aan de praat houden op een moderne Windows. Nu de nieuwe renderer, de HD-textures en de Ultra-preset er staan, is de engine niet langer de grens. Dat zijn de modellen zelf.

Daarom zijn we begonnen met het opnieuw modelleren van de game. Rustig, zorgvuldig, en stuk voor stuk.

Dit is de lange versie van waar dat werk nu staat. Het gaat over drie dingen voor update 0.40: nieuwe 3D-modellen, een vernieuwde interface en een reeks upgrades aan licht en rendering. Er staan meer beelden in dan in alles wat we eerder publiceerden, en de meeste zijn nog vroeg.

> Alles in deze post is **werk in uitvoering**. De renders van de modellen komen uit onze studioscène, niet uit de game. De beelden van de interface en het licht zijn **concept art**: ze tonen de richting, niet het uiteindelijke beeld in de game. 0.40 staat voorlopig gepland voor begin februari 2027. Die datum ligt nog niet vast.

## Nieuwe modellen, vanaf nul gebouwd

De wapens van TC:E waren goed voor hun tijd, maar veel van de first-person wapens bestaan nog altijd uit 500 tot 1.600 driehoeken. Onze HD-textures maakten ze scherper. Ronder konden ze ze niet maken. Een trekkerbeugel die met acht randen is getekend, blijft een achthoek, hoe goed de texture ook is.

We hebben elk model dat de game laadt doorgelopen, meer dan 600 bestanden, en ze gerangschikt op hoeveel een nieuwe versie zou verbeteren aan wat je echt ziet. Veertien first-person wapens draaien nog op hun originele modellen. Handen, granaten, het mes, de bom en de objective-items staan er vlak naast op de lijst.

Daarna bouwden we drie samples om de werkwijze te bewijzen: een pistool, een fragmentatiegranaat en een gevechtsmes. Elk is een nieuw, origineel model, geen opgepoetste versie van het oude. Hieronder staat elk sample naast het model dat het zou vervangen, onder dezelfde lampen en met dezelfde camera.

### Pistool

!compare(img/devlog/models-pistol-today.webp | Nu in de game | img/devlog/models-pistol-new.webp | Nieuw model | Het huidige pistool (698 driehoeken) tegenover de nieuwe P19. Sleep om te vergelijken.)

Het huidige pistool gebruikt 698 driehoeken. De nieuwe P19 is op volle detail gebouwd en komt in de game met ongeveer 9.000 driehoeken en een materiaalset van 2048 pixels: kleur, oppervlaktenormalen, ruwheid en metaal. Daardoor vangen de groeven in de slede, de textuur van de greep en de versleten randen het licht zoals echt metaal en kunststof dat doen.

De opschriften zijn van ons. Elk nieuw wapen krijgt fictieve namen en serienummers.

### Fragmentatiegranaat

!compare(img/devlog/models-grenade-today.webp | Nu in de game | img/devlog/models-grenade-new.webp | Nieuw model | De huidige granaat (612 driehoeken) tegenover het nieuwe M67-model.)

De granaat gaat van 612 naar ongeveer 3.000 driehoeken, met een materiaalset van 1024 pixels. De hendel, de pin en de ring zijn nu aparte onderdelen, wat telt voor de animatie waarin je de pin trekt, en de gestencilde letters zitten in de texture in plaats van er wazig op geschilderd.

### Gevechtsmes

!compare(img/devlog/models-knife-today.webp | Nu in de game | img/devlog/models-knife-new.webp | Nieuw model | Het huidige mes (172 driehoeken) tegenover het nieuwe clip-point mes.)

Het mes maakt de grootste sprong van de drie: 172 driehoeken nu, ongeveer 2.500 voor het nieuwe. Een gestapelde leren greep, een echte stootplaat en een lemmet dat eindelijk een snede heeft.

### Wat er nu gebeurt

Dit zijn renders van de bronmodellen. Voordat een ervan in de game komt, wordt elk model teruggebracht tot zijn budget in de game, geëxporteerd naar het modelformaat van de game en in de engine bekeken op de Ultra-preset, naast de huidige versie. Alleen een model dat er in de game beter uitziet, niet alleen in een studio, vervangt het oude.

De volgorde van het werk volgt de lijst: eerst de kleine items en de oudere wapens, daarna hun third-person versies en accessoires. First-person handen en de spelermodellen komen later, omdat organische vormen eerst een eigen test nodig hebben voordat we ons eraan vastleggen. De spelermodellen houden hetzelfde skelet en hetzelfde silhouet, dus aan de hitregistratie en aan hoe je een speler op afstand herkent verandert niets.

## Elk wapen in de studio

Terwijl de nieuwe modellen gebouwd worden, heeft de interface beelden nodig van de wapens die we vandaag hebben. We renderden alle 41 wapens en granaten uit de eigen modellen van de game, precies zoals de game ze vasthoudt, en belichtten ze in één studio-opstelling. Ze komen op het loadout-scherm, op de MVP-kaart aan het einde van een ronde en op een nieuwe wapendraaitafel.

![Alle 41 wapenrenders](img/devlog/render-arsenal.webp "Alle 41 wapens en granaten, gerenderd uit de eigen modellen van de game.")

![Studiorender van de AK-47](img/devlog/render-ak47.webp "AK-47")

![Studiorender van de SCAR](img/devlog/render-scar.webp "SCAR")

![Studiorender van de M4 SOPMOD](img/devlog/render-m4sopmod.webp "M4 SOPMOD")

![Studiorender van de MP5](img/devlog/render-mp5.webp "MP5")

![Studiorender van de Desert Eagle](img/devlog/render-deagle.webp "Desert Eagle")

Zodra een nieuw model klaar is, maken we zijn render opnieuw vanuit de nieuwe versie.

## Een nieuwe interface: Command

De interface wordt opnieuw ontworpen, van het hoofdmenu tot de laatste regel van het scorebord. We noemen de richting Command: hetzelfde chromen woordmerk en dezelfde rode accenten als de website, donkere glazen panelen met hoekhaken, duidelijke groepering en informatie die je midden in een ronde in één oogopslag leest.

Alle beelden hieronder zijn concept art, gemaakt in 4K over echte opnames uit de game. Lettertypes, witruimte en kleuren komen uit één gedeeld designsysteem, zodat de game, de launcher, de installer en de website eindelijk dezelfde visuele taal spreken.

![Concept van het hoofdmenu](img/devlog/ui-main-menu.webp "Hoofdmenu: snel meedoen, live spelersaantallen en het laatste nieuws op het eerste scherm.")

![Concept van het menu in de game](img/devlog/ui-esc.webp "Het menu in de game opent als zijpaneel, met de live score en je gameversie.")

![Concept van de HUD](img/devlog/ui-hud.webp "HUD: rustiger, lichter en leesbaar op elke map.")

![Concept van het scorebord](img/devlog/ui-scoreboard.webp "Scorebord")

![Concept van het deployment-scherm](img/devlog/ui-deploy.webp "Deployment: kies je team, uitrusting en wapens op één plek.")

![Concept van de opties](img/devlog/ui-options.webp "Opties, gegroepeerd zoals je ze zoekt, met een live voorbeeld.")

### De match, van laadscherm tot mapstemming

![Concept van het laadscherm](img/devlog/ui-loading.webp "Laadscherm met de briefing van de map.")

![Concept van de rondebanner](img/devlog/ui-round.webp "Banner bij de start van een ronde.")

![Concept van de bommelding](img/devlog/ui-bomb.webp "Bommelding, teamlijst en richtingsmarkeringen in een live ronde.")

![Concept van de MVP-kaart](img/devlog/ui-mvp.webp "MVP-kaart aan het einde van een ronde.")

![Concept van de mapstemming](img/devlog/ui-vote.webp "Stemmen over de volgende map aan het einde van een match.")

![Concept van de spelerskaart](img/devlog/ui-player-card.webp "Je spelerskaart in het hoofdmenu.")

### Het fijne werk

De kleine dingen tellen net zo zwaar als de schermen. Elk wapen krijgt een strak HD-icoon. De menu's bewegen met korte, zachte overgangen in plaats van in beeld te springen. Elke knop krijgt echte hover-, ingedrukt- en focusstatussen, en de hele interface werkt met het toetsenbord. Een nieuwe serverbrowser laat zien wat er op elke server gebeurt voordat je meedoet. Kleurenblinde presets en een instelling voor de tekstgrootte zitten ook in het plan.

![Concept van de HD-wapeniconen](img/devlog/ui-icons.webp "Eén strakke iconenset voor elk wapen.")

![Concept van de wapendraaitafel](img/devlog/ui-turntable.webp "Wapendraaitafel op het loadout-scherm.")

![Concept van de serverbrowser](img/devlog/ui-servers.webp "De nieuwe serverbrowser.")

![Concept van de interfacestatussen](img/devlog/ui-states.webp "Cursor-, hover- en focusstatussen.")

### Scherpere vizieren

De richtkruizen in de vizieren waren op een heel lage resolutie getekend, soms maar 64 bij 64 pixels, en dat zag je elke keer dat je richtte. We hebben ze allemaal opnieuw getekend op vier keer de resolutie. Elk richtkruis houdt precies hetzelfde richtpunt, dus aan hoe een vizier schiet verandert niets. Het ziet er alleen uit als glas in plaats van pixels.

!compare(img/devlog/reticle-eotech-old.webp | Nu | img/devlog/reticle-eotech-new.webp | Opnieuw getekend | Het richtkruis van het holografische vizier, nu en opnieuw getekend op vier keer de resolutie.)

![Concept van de HD-richtkruizen](img/devlog/ui-reticles.webp "De nieuwe richtkruizen in de vizieren die ze gebruiken.")

### Installer en studio-intro

De installer krijgt dezelfde behandeling, zodat het eerste wat een nieuwe speler ziet al aanvoelt als de game die hij gaat spelen.

!compare(img/devlog/installer-old.webp | Nu | img/devlog/installer-new.webp | Nieuw | De welkomstpagina van de installer, nu en in de nieuwe stijl.)

![Concept van de studio-intro](img/devlog/ui-splash.webp "Studio-intro en titelreeks.")

![Key art](img/devlog/store-key-art.webp "Nieuwe key art voor winkelpagina's en pers.")

## Nieuw licht

Het derde deel van het werk is de renderer. De maps van TC:E zijn jaren geleden één keer belicht, en veel van dat licht zit in de textures zelf. De upgrades hieronder laten het licht zich gedragen zoals het hoort: explosies die de muren verlichten, lampen die schaduw werpen, nevel die diepte heeft.

Elk beeld in dit deel is een geschilderde impressie over een echte Ultra-opname uit de huidige build. Het eindresultaat zal er op plaatsen anders uitzien, en we tonen echte opnames uit de game zodra elk onderdeel af is.

> Geen van deze upgrades verandert wat je in Ranked kunt zien. Mist, nevel en licht houden hetzelfde zicht, zodat niemand voordeel haalt uit een grafische instelling.

### Dynamisch licht

!compare(img/devlog/engine-m3-dynamic-lights-now.webp | Nu | img/devlog/engine-m3-dynamic-lights-concept.webp | Concept | Een explosie verlicht de muur, de vloer en de speler ernaast.)

Vandaag kunnen maar een paar lichtbronnen tegelijk een oppervlak raken. Het nieuwe systeem verlicht de wereld en de spelers vanuit elke bron in de buurt, met fysiek correcte materialen, zodat mondingsvuur, explosies en fakkels hun omgeving echt verlichten.

### Lucht en atmosfeer

!compare(img/devlog/engine-m4-sky-now.webp | Nu | img/devlog/engine-m4-sky-concept.webp | Concept | Een fysieke lucht met nevel in de verte, bij hetzelfde zicht.)

### Kogelgaten met diepte

!compare(img/devlog/engine-m5-decals-now.webp | Nu | img/devlog/engine-m5-decals-concept.webp | Concept | Inslagen met afgebrokkelde randen, barsten en stof die het oppervlak volgen.)

### Deeltjes

!compare(img/devlog/engine-m6-particles-now.webp | Nu | img/devlog/engine-m6-particles-concept.webp | Concept | Explosies met tien keer zoveel deeltjes: vonken, puin en stof.)

### HD-textures voor de wereld

!compare(img/devlog/engine-m1-hd-textures-now.webp | Nu | img/devlog/engine-m1-hd-textures-concept.webp | Concept | Baksteen op Village, van dichtbij, met volledig materiaaldetail.)

Nieuwe textures in hoge resolutie met volledige materiaalkaarten voor de wereld. Ze worden een optionele download van ongeveer 1 GB, aangeboden bij de Ultra-preset, zodat niemand met een tragere verbinding of een oudere pc ze hoeft te nemen.

### Opnieuw berekend licht

!compare(img/devlog/engine-m2-lightmaps-now.webp | Nu | img/devlog/engine-m2-lightmaps-concept.webp | Concept | Railhouse met opnieuw berekend licht: weerkaatsend licht, zachte schaduwen en contactschaduwen.)

Op de kernmaps wordt het licht opnieuw berekend, met licht dat van oppervlakken terugkaatst en schaduwen die zachter worden met de afstand. Als een map niet nauwkeurig genoeg overeenkomt met hoe hij vandaag speelt, houdt hij zijn huidige licht.

### Weerkaatsend licht

!compare(img/devlog/engine-m7-bounce-now.webp | Nu | img/devlog/engine-m7-bounce-concept.webp | Concept | Licht dat in realtime van muren en vloeren terugkaatst, op Ultra.)

### Verlichte mist

!compare(img/devlog/engine-m8-lit-fog-now.webp | Nu | img/devlog/engine-m8-lit-fog-concept.webp | Concept | Lampen die de lucht om zich heen verlichten en de schaduw respecteren van wat in de weg staat.)

### Lampschaduwen

!compare(img/devlog/engine-m9-lamp-shadows-now.webp | Nu | img/devlog/engine-m9-lamp-shadows-concept.webp | Concept | Binnen- en straatlampen die echte schaduw werpen, op High en Ultra.)

De DirectX 12-renderer krijgt dit allemaal. De OpenGL-renderer krijgt de HD-textures, het opnieuw berekende licht, de nieuwe kogelgaten en de nieuwe deeltjes.

## Hoe het getest wordt

Niets hiervan komt in de game omdat het er op een plaatje goed uitziet. Elk nieuw model wordt in de game bekeken naast het model dat het vervangt. Elk interfacescherm wordt vastgelegd op 1080p, 1440p, 4K en ultrawide en vergeleken met zijn concept. Elke lichtfunctie heeft een prestatiebudget waar ze binnen moet blijven, en de volledige regressietest dekt beide renderers, de server en de launcher voordat een release wordt verpakt.

Haalt iets de lat niet, dan wacht het op de volgende update. We brengen liever een kleinere 0.40 uit die werkt dan een grotere die dat niet doet.

## Wat je mag verwachten

0.40 wordt de grootste update die Platinum tot nu toe kreeg: de nieuwe interface, het lichtwerk en de eerste golf nieuwe modellen. Ze staat voorlopig gepland voor begin februari 2027. Die datum ligt nog niet vast, en we bevestigen hem hier zodra de laatste testronde achter de rug is.

Het hermodelleren stopt niet bij 0.40. Het is een lang project, en we blijven voor-en-na-beelden posten telkens als een nieuw model in de game komt. Laat ons weten wat je ervan vindt in de reacties hieronder, of op [Discord](https://discord.gg/7Dg4yhhvGF). Welk model moeten we als volgende opnieuw bouwen?
