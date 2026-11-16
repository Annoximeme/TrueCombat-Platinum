---
title: Inside 0.37.1, bijgesteld op jullie meldingen
date: 2026-11-15
time: 11:30
summary: Een HUD die je op je scherm afstemt, een magazijn- en gezondheidsweergave in de geest van het origineel, wapens weer op hun echte vuursnelheid, soepeler laden van kaarten en optionele HD-texturen. Dit is wat er in 0.37.1 veranderd is, en waarom.
image: img/hero-snow-warehouse.webp
tag: Release
version: 0.37.1
---
0.37.0 was de grootste update die Platinum ooit gehad heeft, en zette in één keer veel nieuws voor veel spelers neer. Jullie lieten snel weten wat goed voelde en wat niet. Versie 0.37.1 is ons antwoord op die meldingen. Het is een vervolg en geen nieuwe lading functies, maar klein is het niet: de update raakt de HUD, de gunplay, de bots, de prestaties en de launcher.

> De launcher installeert 0.37.1 vanzelf en je instellingen blijven behouden. Wil je een kleinere installatie, dan kun je HD-texturen nu uitschakelen in de launcher.

## Een HUD die bij je scherm past

De nieuwe interface in 0.37.0 kwam met drie vaste menugroottes. Dat bleek niet genoeg. Spelers met grote monitoren wilden een kleinere HUD, spelers op een laptop een grotere, en bijna iedereen wilde de chat minder in de weg.

Daarom zijn de groottes nu schuifregelaars. **Menugrootte** loopt van 50 tot 100 procent en **Grootte in-game UI** van 50 tot 150 procent, allebei in stappen van 5 procent. De doorzichtigheid is in drieën gesplitst: je kunt de HUD-panelen vervagen zonder de tekst en icoontjes erop kwijt te raken, en de chat apart instellen. De rondetimer en de teamscores kun je elk afzonderlijk tonen of verbergen.

Een paar dingen gingen ook uit de weg. De melding "You killed" midden in beeld is verdwenen, want die bedekte precies de plek waar je op richtte. De doodskaart staat nu rechtsonder en verdwijnt na ongeveer tweeënhalve seconde. De laadschermen van de kaarten zijn terug, en de optie voor de FPS-teller doet eindelijk wat ze belooft.

Ook de toetstoewijzing had twee eigen problemen. **Standaardinstellingen** zet nu de juiste Platinum-indeling terug, en de launcher overschrijft geen toetsen meer die je in het spel hebt aangepast. Nieuwe spelers krijgen bovendien meteen **F3** om een stemming te starten.

## Munitie en gezondheid, zoals vroeger

Het originele TrueCombat toonde nooit hoeveel kogels je nog had. Je zag een magazijn en hoeveel reservemagazijnen je bij je droeg, en je leerde je schoten tellen. 0.37.1 brengt dat terug. Het munitiepaneel toont een magazijnicoon met het exacte aantal reservemagazijnen, samen met het icoon van het wapen dat je vasthoudt. Wil je weten hoe vol je huidige magazijn is, dan vertelt de nieuwe toets **Magazijn controleren** het je.

Om dezelfde reden is de herlaadmelding verdwenen. In de plaats daarvan klikt een leeg wapen luider, zodat je meteen weet dat je droog staat.

Gezondheid werkt in dezelfde geest. Een silhouet van je lichaam laat zien waar je geraakt bent, en waarschuwt als je mank loopt of bijna dood bent. In ranked matches krijg je alleen het silhouet, zodat iedereen dezelfde informatie ziet. In unranked kun je exacte gezondheidscijfers aanzetten in de opties als je dat liever hebt.

## Wapens weer op hun echte snelheid

Vuursnelheid was na 0.37.0 een van de meest gehoorde opmerkingen. We hebben elk wapen naast het originele TrueCombat:Elite gelegd en de wapens die waren afgeweken rechtgezet:

- Automatische wapens vuren precies op hun oorspronkelijke snelheid.
- Grendelgeweren herladen weer op hun oorspronkelijke tempo.
- Pompgeweren hebben nu een volledige pompbeweging tussen twee schoten nodig, waardoor ze weer op de juiste snelheid vuren. Ook het herlaadgeluid is opgelost: één patroon, één geluid, in plaats van een dubbel en vertraagd effect.

Bij het sprinten kozen we bewust voor een verandering. In het origineel kon je blijven sprinten terwijl je door het vizier richtte, en zelfs met een lege staminabalk. Dat zijn trouwe details, maar in de praktijk voelden gevechten daardoor niet juist, en het was een van de duidelijkste klachten uit de playtests. In 0.37.1 stopt je sprint zodra je richt, en met een lege staminabalk sprint je niet meer. De oorspronkelijke kost van springen tijdens het sprinten blijft ongewijzigd.

Verschillende visuele details staan weer waar ze horen. Wisselen van wapen speelt de juiste animatie af, granaatexplosies zien er weer uit zoals in het origineel, in zowel DirectX 12 als OpenGL, elke klasse gebruikt haar eigen personagemodel, en een geworpen fraggranaat lijkt in de lucht niet langer op een rookgranaat. Kogelgaten en bloed worden aan het begin van elke ronde opgeruimd, en in randloos venstermodus blijft de muis op het scherm van het spel.

## Bots

Bots vinden hun weg op de kaarten beter. Verbeterde routeplanning zorgt ervoor dat ze minder vast komen te zitten en betere routes kiezen, en ze blijven beter uit je vuurlijn.

## Soepeler laden van kaarten

Sommigen van jullie merkten een hapering telkens als een nieuwe kaart begon. De oorzaak was een grafische cache die één keer per kaart opgebouwd moest worden, maar bij elke keer laden opnieuw werd gemaakt. Die wordt nu één keer opgebouwd, op de achtergrond bewaard en hergebruikt, zodat de eerste seconden van een kaart even soepel lopen als de rest.

Daarnaast hebben we verschillende gevallen opgelost waarin het spel kon blijven hangen tijdens het opstarten of bij het verbinden. Frame Generation pauzeert nu als het spel geminimaliseerd is of op de achtergrond staat. Negen geluiden die ontbraken, zijn terug. En het consolelogboek van je vorige sessie wordt nu bewaard, waardoor je crashmeldingen voor ons veel bruikbaarder worden.

## Graphics

Meer texturen in de wereld hebben nu speculaire details op de Ultra-preset, voor een rijker en gedetailleerder beeld van dichtbij. HDR-reflecties zijn bijgesteld voor een natuurlijkere look.

## Namen, accounts en meldingen

Oranje is nu voor iedereen beschikbaar in de kleurkiezer voor namen. Accounthouders van wie het account even nodig had om geverifieerd te worden, kwamen soms binnen als "Player####". Dat gebeurt niet meer: je naam wordt hersteld zodra de controle klaar is. Foutmeldingen via **F12** bewaren je concept nu tot ze echt verstuurd zijn, zodat een verbroken verbinding je niet meer kost wat je geschreven had.

Daarnaast hebben we onze beveiligingsmaatregelen aangescherpt en uitgebreid.

## Launcher 2.5

De grootste verandering in de launcher is keuze. **HD-texturen zijn nu optioneel.** Schakel ze uit via **Instellingen > Updates** om schijfruimte en downloadtijd te besparen. Je kunt nog steeds op elke server spelen zonder ze eerst te downloaden, en als je ze weer aanzet, haalt de launcher op wat ontbreekt.

De rest is afwerking. De nieuwspagina en de patch notes laden weer. "What's New" overlapt de Support-knop niet meer, en de indeling blijft overeind in gemaximaliseerde en grotere vensters. Er draait nog maar één launcher per installatie, dus dubbele icoontjes in het systeemvak zijn verleden tijd. Je bureaubladsnelkoppeling overleeft voortaan updates. De downloadvoortgang leest duidelijker, en de Duitse, Franse en Poolse vertalingen zijn verbeterd.

## Een nieuwe intro

Het spel opent nu met een kaart van Team Terminus, gevolgd door het Platinum-logo. Die vervangen de oude intromovies en afsluitschermen. De intromuziek is "Venom" van Scott Buckley, gebruikt onder de CC BY 4.0-licentie.

## Hoe we het getest hebben

0.37.1 ging door dezelfde releasetests als elke versie ervoor: de volledige regressietests voor beweging, gevechten, netwerkgevoel, graphics, instellingen en herstarts, in zowel DirectX 12 als OpenGL, plus het updatepad van de launcher. Elke fix in deze release is bovendien apart getest voordat hij werd samengevoegd, en de timing van de wapens is vergeleken met het originele spel.

## Nog op onze lijst

Eén melding uit 0.37.0 is in deze release nog niet opgelost. Bij sommige spelers valt al het geluid weg na alt-tab of na een wijziging aan hun audioapparaat, en het blijft stil tot ze het spel herstarten. We weten nu waarom dat gebeurt, en een fix wordt getest voor een volgende update. Tot dan brengt een herstart van het spel het geluid terug.

Zoals altijd: als iets niet goed voelt, druk dan op **F12** in het spel om ons een melding te sturen. Deze update bestaat omdat jullie dat deden. Bedankt voor het spelen.
