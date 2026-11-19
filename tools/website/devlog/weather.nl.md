---
title: Storm boven Northport
date: 2026-11-19
time: 04:30
summary: Regen, onweer, doorweekte straten na de regen, sneeuw en wind. Elke map bepaalt nu zijn eigen weer bij het laden, voor elke speler op de server hetzelfde, en het laadscherm vertelt je wat er komt.
image: img/devlog/weather-northport-storm.webp
tag: Graphics
version: 0.39.4
---
Northport zag er altijd uit alsof het elk moment kon gaan regenen. Grijs water, rode loodsen, plassen op de kades die nooit opdrogen. Twintig jaar lang kwam die regen nooit. In 0.39.4 komt hij wel.

Elke map bepaalt nu zijn eigen weer bij het laden: helder, bewolkt, regen, een echt onweer, het doorweekte uur na de regen, sneeuw of een winderige dag. Het is geen instelling en geen decor dat alleen sommige spelers zien. De server kiest het weer, elke speler op die server krijgt precies dezelfde lucht, en het laadscherm vertelt je waar je in terechtkomt voordat je spawnt.

![Onweer boven Northport op de Ultra-preset](img/devlog/weather-northport-storm.webp "Zware regen en een zwarte lucht boven de werf van Northport. Ultra-preset, DirectX 12.")

## Waarom weer, en waarom voor iedereen

Een map die je duizend keer gespeeld hebt, voelt op den duur niet meer als een plek. Weer is de eenvoudigste manier om er weer een plek van te maken. Dezelfde werf leest anders als het licht vlak wordt, de grond donker kleurt en elk oppervlak sist van de regen. Je beweegt anders, je luistert anders, en de ronde die je onthoudt is "die in de storm".

We hebben lang nagedacht over een optie. We hebben het niet gedaan. Als de ene speler regen uitzet en de andere niet, spelen ze niet meer dezelfde ronde: de een ziet een schoner beeld, de ander hoort een voetstap door de regen heen. Er is dus geen schakelaar. Het weer hoort bij de ronde, net als de map. Daardoor moesten we elk soort weer ook zo bouwen dat het een andere speler nooit slechter zichtbaar maakt. Daarover verderop meer.

## Hoe een ronde aan zijn weer komt

Als een map laadt, gooit de server het weer uit een tabel die voor die map gemaakt is. Die worp geeft drie dingen: het soort weer, hoe sterk het is en een seed. Die gaan naar elke speler, en al de rest wordt daaruit opgebouwd op elke pc: waar de regen valt, hoe de windstoten aanzwellen, wanneer en waar de bliksem inslaat. Twee spelers aan weerszijden van de map zien dezelfde flits op hetzelfde moment, en allebei horen ze de donder aankomen wanneer dat hoort.

Het weer blijft de hele map. Van warmup naar de match wordt het niet opnieuw bepaald, dus wat het laadscherm beloofde, is wat je speelt.

Elke map heeft zijn eigen kansen:

- **Northport** is de regenmap. Ongeveer de helft van de rondes brengt regen of onweer, en nog eens een op de zes is het uur na de regen, met doorweekte, druppende kades. De rest is bewolkt, helder of winderig.
- **Harbour** volgt kort daarna, met iets minder storm.
- **Snow, Snowtown en de villa** krijgen meestal sneeuw, van een paar vlokken tot een sneeuwstorm. De rest is grijs of winderig.
- **Delta, Village, Railhouse, Stadtrand en de andere maps** krijgen een mix die neigt naar heldere luchten, met Delta als winderigste.

![Het laadscherm met het weer van de ronde](img/devlog/weather-loading-screen.webp "Het laadscherm toont het weer naast het mapplan, zodat je weet waar je in terechtkomt.")

## Op het laadscherm

Je ziet het weer voordat je de map ziet. In de hoek van het mapvoorbeeld op het laadscherm staat een klein label: **CLEAR**, **OVERCAST**, **LIGHT RAIN**, **HEAVY RAIN**, **THUNDERSTORM**, **AFTER THE RAIN**, **SNOW**, **HEAVY SNOW**, **WINDY**. Het is iets kleins, maar het zet de sfeer terwijl de map laadt, en bij een stormronde vertelt de gele streep je dat er bliksem aankomt.

## Regen

Regen is het hart van deze update, en daar zat het meeste werk in.

Een regendruppel in TrueCombat is een dunne streep die valt volgens zijn eigen snelheid en die van de wind, dus een windstoot laat de regen zichtbaar schuin hangen. Er vallen er tot 2.600 tegelijk in een brede cirkel rond je heen, meer dichtbij waar je ze ziet en minder ver weg waar ze alleen ruis zouden zijn. Strepen vlak voor je ogen vervagen, zodat de regen nooit een felle streep over je vizier legt. Verre strepen blijven ongeveer een pixel breed, zodat een stortbui dicht oogt zonder een grijze muur te worden.

Het moeilijke is weten waar regen kan vallen. Regen die door een dak valt, is de snelste manier om het effect te verpesten. Het spel kijkt naar de lucht boven elk stukje grond rond je. Onder een dak, een luifel of een overkapping valt niets. In de open lucht landt elke druppel op de echte grondhoogte, dus hij verdwijnt niet in het niets en valt niet door een krat. Die controle wordt per stukje grond bewaard en over meerdere frames gespreid, zodat ze bijna niets kost zodra je rondgekeken hebt.

Als een druppel landt, spat hij:

- **Op water en plassen** loopt er een kring over het oppervlak. Het havenbekken van Northport danst in een storm.
- **Op harde grond** springt er een klein kroontje water op en loopt er een kleine kring uit.

Regen verandert ook de grond zelf. Op DirectX 12 met Ultra-materialen volgen de natte plekken die we in 0.39.0 invoerden nu het weer. Lichte regen maakt een deel van de grond donker, zware regen doorweekt bijna alles, en plassen glanzen. Dat werkt op elke map, niet alleen op de maps die al natte plekken hadden.

![Regen die op de kades van Northport spat](img/devlog/weather-northport-rain.webp "Regen op de kades: elke druppel landt op de echte grond en spat, en in plassen lopen kringen. Ultra-preset.")

## Onweer

Onweer is regen op zijn sterkst: de zwaarste stortbui, harde windstoten die de regen schuin blazen, een donkere bewolkte lucht en bliksem.

We hebben lang nagedacht over waar de bliksem moest inslaan. Onze eerste versie sloeg in binnen de map. Dat zag er geweldig uit op een screenshot en slecht in een gevecht: een witte lijn door het midden van je beeld terwijl je een straat afmikt, is afleiding en geen sfeer. Daarom slaat de bliksem nu in **voorbij de rand van de map**, van hoog in de wolken tot achter de daken. Je ziet hem boven de gebouwen, de lucht flikkert, en even later rolt de donder binnen. Hij slaat nooit in tussen jou en de speler op wie je mikt.

Elke inslag heeft een eigen vorm, een grillige schicht met een zachte gloed rond een witte kern, en hij flikkert zoals de echte: een felle eerste ontlading en daarna twee of drie zwakkere over ongeveer een halve seconde. Het beeld krijgt op hetzelfde moment een korte, zwakke flits, veel zwakker als je binnen staat.

De donder komt van de nieuwe weergeluiden in dezelfde update. Hij reist aan de snelheid van het geluid, dus een inslag op 3.000 eenheden afstand hoor je meer dan een vijfde seconde nadat je hem ziet. Dichtbij kraakt en knalt het, ver weg rommelt het laag, en binnen klinkt het gedempt. Omdat elke speler dezelfde inslagen op hetzelfde moment krijgt, hoort iedereen dezelfde storm.

![Bliksem boven de daken van Northport](img/devlog/weather-northport-lightning.webp "De bliksem slaat in voorbij de map, boven de daken: je ziet hem, en even later hoor je hem. Ultra-preset.")

## Na de regen

Onze favoriet is de stilste. Na de regen is de storm voorbij maar is de wereld nog niet droog: de grond is doorweekt, plassen glanzen, er vallen nog een paar laatste druppels, rond je druppelt water en je voetstappen klinken nat. De zon komt met minder dan de helft van zijn kracht terug door de dunner wordende wolken.

Het is de ronde waarin de map er het meest anders uitziet en precies hetzelfde speelt. Er hangt niets in de lucht en er is niets om doorheen te kijken, alleen een nattere, koudere versie van een plek die je kent.

![Northport na de regen](img/devlog/weather-northport-afterrain.webp "Na de regen: doorweekte grond, glanzende plassen en een koud licht. Ultra-preset.")

## Sneeuw

De sneeuwmaps hadden altijd al een beetje sneeuwval. Nu komt en gaat die met het weer, van een paar trage vlokken tot een zware sneeuwval die op de wind drijft. Elke vlok wiegt op zijn eigen baan, en net als de regen valt hij alleen waar de lucht open is. Als het weer sneeuw brengt, vervangt dat de eigen sneeuwval van de map, zodat de twee nooit opgestapeld worden.

![Zware sneeuw op Snow](img/devlog/weather-snow.webp "Een zware sneeuwval die op de wind drijft. Ultra-preset.")

## Wind en bewolking

Een winderige ronde waait harder: de windstoten die al sneeuw en bladeren bewogen, zijn sterker en sneller, gruis scheert met de windstoten over de grond, en bladeren waaien over elke map, niet alleen over de groene. Het windgeluid dat je hoort, volgt dezelfde windstoten.

Bewolkt is het eenvoudigste weer en verandert de map meer dan je zou denken. De lucht wordt een laag grijs wolkendek, de zonnestralen en de schittering verdwijnen, en de kleur koelt een tikje af.

## Eerlijk in Ranked

Weer in een competitieve shooter is alleen leuk als het eerlijk is. Elke regel hier komt uit één vraag: maakt dit een andere speler slechter zichtbaar of hoorbaar?

- **Iedereen krijgt hetzelfde weer.** De server kiest het en elke speler ziet het. Er is geen optie om regen uit te zetten voor een schoner beeld.
- **De kleurverandering raakt de helderheid nooit.** Regen en storm maken de kleur iets kouder en minder verzadigd, maar helderheid en contrast blijven precies waar ze waren, dus een speler in een deuropening is in een storm even goed zichtbaar als op een heldere dag.
- **In Ranked en clanmatches is de zware kant begrensd.** Elk soort weer kan nog altijd vallen, maar regen, storm en sneeuw blijven op een gematigde sterkte, en de bliksemflits is half zo fel.
- **Regen verbergt nooit voetstappen.** De regengeluiden zitten ruim onder de stilste voetstap, en ze dippen even als een andere speler vlak bij je stapt.
- **Mist en het gouden uur zitten niet in deze update.** Ze staan allebei op ons lijstje, maar mist is precies het soort weer dat spelers verbergt, en dat willen we goed doen voordat het in een match kan vallen.

## Prestaties

Het weer wordt getekend door je grafische kaart, zonder nieuwe bestanden om te downloaden en met hetzelfde beeld op DirectX 12 en OpenGL, Remastered en Classic. De natte grond en de kleurverandering hebben DirectX 12 met Ultra-materialen nodig. Al de rest zie je op elke preset. Regen is het zwaarste weer, en het is gebouwd om goedkoop te blijven:

- druppels achter je worden helemaal niet getekend,
- de luchtcontrole wordt bewaard en over frames gespreid,
- het aantal druppels stijgt en daalt met de sterkte van de regen, en bij een gewone heldere ronde draait er helemaal niets.

## Voor serverbeheerders

Weer staat standaard aan en wordt vanzelf bepaald. Voor evenementen kun je een weer op je server vastzetten, bijvoorbeeld een storm met een vaste sterkte. Ranked-servers houden de grenzen hierboven, wat je ook kiest.

## Getest

We hebben het weer getest op elke map, in elk weer, met bots die lange rondes vochten op Northport en Snow in willekeurig weer, en met de server en beide spelbuilds gecontroleerd op Windows en Linux. De timing van de inslagen, de lucht en het laadscherm zijn naast elkaar gecontroleerd, zodat elke speler dezelfde ronde ziet.

Sommige dingen zie je alleen op een echt scherm, dus de laatste ronde gebeurt op onze eigen pc's voordat 0.39.4 uitkomt: de dichtheid van de regen tegen de lucht van elke map, de spatten op DirectX 12 en de framerate in de zwaarste storm.

> De volgende keer dat je Northport inlaadt en het label zegt THUNDERSTORM, blijf dan even op de kade staan voordat je begint te lopen. Luister naar de donder.

Tot in de regen.
