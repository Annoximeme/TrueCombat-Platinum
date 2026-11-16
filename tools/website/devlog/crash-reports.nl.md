---
title: Crashes oplossen op de pc's waarop jullie echt spelen
date: 2026-11-16
time: 16:00
summary: De launcher kan ons nu vertellen waar de game crashte en op welke hardware hij draait, als jij ja zegt. Hij vraagt het één keer, het is anoniem en je ziet het exacte rapport voordat het je pc verlaat.
image: img/devlog/launcher-2-play.webp
tag: Launcher
version: 0.38.0
---
Als de game op jouw pc crasht, horen wij daar meestal niets van. De launcher bewaart al een crashrapport naast de game en biedt aan om het in een probleemrapport te stoppen, maar dat komt alleen bij ons als je het inpakt en opstuurt. De meeste mensen starten de game, heel begrijpelijk, gewoon opnieuw.

Dan blijft het voor ons gissen. Is een crash in de DirectX 12-renderer één speler met een oude driver, of elke tweede laptop met een bepaalde grafische chip? Playtests vangen veel op, maar ze draaien op een handvol machines.

## Eén vraag, één keer

De volgende update voegt een kleine kaart toe aan de Spelen-pagina van de launcher. Die vraagt of je anonieme crash- en hardwaregegevens wilt delen, met twee even zware knoppen: **Delen** en **Nee, bedankt**. Wat je ook kiest, hij vraagt het niet opnieuw. Je kunt je antwoord altijd wijzigen bij Instellingen > Privacy.

Er wordt niets verstuurd voordat je kiest, en helemaal niets als je nee zegt.

## Wat een rapport bevat

Staat delen aan, dan stuurt de launcher hoogstens één kort rapport per dag, en alleen als er iets nieuws is:

- **Crashes.** Welk programma crashte (game of server), de Windows-foutcode en de plek in het programma waar het gebeurde, als bestandsnaam en positie, plus tot vijf stappen die eraan voorafgingen. Precies wat we nodig hebben om de verantwoordelijke regel code te vinden, met de symboolbestanden die we van elke build bewaren.
- **Gamestarts.** Hoe vaak de game sinds het vorige rapport startte en hoeveel daarvan een Veilige start waren. Zo worden crashaantallen een crashpercentage per versie, en zien we meteen of een update het beter of slechter maakte.
- **Hardware, één keer per maand.** Windows-versie, processor, werkgeheugen, grafische kaart, videogeheugen, of DirectX 12 werkt, bureaubladresolutie en verversingssnelheid.

## Wat er nooit in staat

Geen spelnaam, geen gamesleutel, geen speler-ID, geen installatie-ID, geen bestandspaden, geen serveradressen en geen IP-adres. Niets in een rapport koppelt het aan het volgende, dus we kunnen niet eens zien of twee rapporten van dezelfde pc komen. Crashrapporten en geheugendumps blijven op je pc.

> Zelf kijken? Instellingen > Privacy > Wat wordt gedeeld toont precies het rapport dat je pc als volgende zou versturen, voordat er iets je computer verlaat.

## Wat we ermee doen

De cijfers komen op hetzelfde besloten dashboard dat websitebezoeken telt: crashes gegroepeerd per plek, een crashpercentage per gameversie, en welke grafische kaarten, processors en schermformaten onze spelers gebruiken. Zo weten we waar we onze tijd in moeten steken, en welke instellingen en presets we moeten afstemmen op de hardware die jullie echt hebben.

Crashgegevens bewaren we 90 dagen, hardwaretellingen 13 maanden. De [privacypagina](privacy.html#launcher) heeft de volledige lijst, en zoals altijd staat de code die de rapporten ontvangt in de openbare repository.
