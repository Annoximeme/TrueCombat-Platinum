"""The download, FAQ, TrueCombat: Elite and privacy pages, in English and Dutch.

Unlike the hand-edited pages, these three are written out in full by build.py:
the markup lives once in the templates below and the copy in the EN and NL
tables, so a change here never needs a matching pair in nl.py. The download
page takes its version, size, date and link from the home page, which the
release workflow keeps current.

Placeholders: [[key]] is copy from the language table, {{name}} is a value
build.py fills in (version, link, asset prefix).
"""

ART = {"download": "map-northport", "faq": "hero-stadtrand-canal", "truecombat-elite": "map-delta", "privacy": "map-stadtrand"}

DOWNLOAD_SVG = '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 3v12m0 0l-5-5m5 5l5-5M4 19h16" stroke="currentColor" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'

# ---------------------------------------------------------------- download
DOWNLOAD = """<section class="page-head">
  <div class="head-art" style="--art: url({{up}}img/map-northport.webp); --art-s: url({{up}}img/map-northport-640.webp)" aria-hidden="true"></div>
  <div class="wrap">
    <span class="eyebrow">[[eyebrow]]</span>
    <h1>[[h1]]</h1>
    <p class="lede">[[lede]]</p>
  </div>
</section>

<section class="band download">
  <div class="wrap dl-grid">
    <div class="dl-main">
      <div class="hero-cta">
        <a class="btn btn-play" data-download href="{{link}}">
          """ + DOWNLOAD_SVG + """
          <span class="stack"><span class="big">Download <span data-version>{{version}}</span></span><span class="small"><span data-kind="long">{{kind}}</span> · <span data-size>{{size}}</span> · <span data-date>{{date}}</span></span></span>
        </a>
        <a class="btn btn-ghost" href="https://github.com/Annoximeme/TrueCombat-Platinum/releases">[[all]]</a>
        {{scan_chip}}
      </div>
      <ol class="steps">
        <li><span>[[s1]]</span></li>
        <li><span>[[s2]]</span></li>
        <li><span>[[s3]]</span></li>
      </ol>
      <p class="yt-note">[[note]]</p>
    </div>
    <div class="reqs">
      <h2>[[need]]</h2>
      <dl>
        <dt>[[r1t]]</dt><dd>[[r1]]</dd>
        <dt>[[r2t]]</dt><dd>[[r2]]</dd>
        <dt>DLSS / DLAA</dt><dd>[[r3]]</dd>
        <dt>[[r4t]]</dt><dd>[[r4]]</dd>
        <dt>[[r5t]]</dt><dd>[[r5]]</dd>
        <dt>[[r6t]]</dt><dd>[[r6]]</dd>
      </dl>
    </div>
  </div>
</section>

{{scan_panel}}

<section class="band" id="included">
  <div class="wrap">
    <div class="section-head">
      <span class="eyebrow">[[in_eyebrow]]</span>
      <h2>[[in_h]]</h2>
    </div>
    <div class="features">
      <div class="feature"><h3>[[f1t]]</h3><p>[[f1]]</p></div>
      <div class="feature"><h3>[[f2t]]</h3><p>[[f2]]</p></div>
      <div class="feature"><h3>[[f3t]]</h3><p>[[f3]]</p></div>
    </div>
  </div>
</section>

<section class="band band-alt" id="first-match">
  <div class="wrap">
    <div class="section-head">
      <span class="eyebrow">[[go_eyebrow]]</span>
      <h2>[[go_h]]</h2>
    </div>
    <ol class="steps-flow">
      <li><b>[[g1t]]</b><p>[[g1]]</p></li>
      <li><b>[[g2t]]</b><p>[[g2]]</p></li>
      <li><b>[[g3t]]</b><p>[[g3]]</p></li>
    </ol>
    <p class="steps-note">[[acct]]</p>
  </div>
</section>

<section class="band" id="help">
  <div class="wrap">
    <div class="section-head">
      <span class="eyebrow">[[help_eyebrow]]</span>
      <h2>[[help_h]]</h2>
    </div>
    <div class="faq">
      <div><h3>[[h1t]]</h3><p>[[h1a]]</p></div>
      <div><h3>[[h2t]]</h3><p>[[h2a]]</p></div>
      <div><h3>[[h3t]]</h3><p>[[h3a]]</p></div>
      <div><h3>[[h4t]]</h3><p>[[h4a]]</p></div>
    </div>
    <p class="more-row"><a class="btn btn-ghost" href="faq.html">[[help_all]]</a></p>
  </div>
</section>
"""

DOWNLOAD_T = {
    "en": {
        "title": "Download TrueCombat: Platinum · Free for Windows 10 and 11",
        "desc": "Download TrueCombat: Platinum free for Windows 10 and 11. One small installer sets up the full game and the launcher, with no separate TC:E or Enemy Territory install.",
        "og": "Free download for Windows 10 and 11. One small installer, the full game, signed updates.",
        "eyebrow": "Download", "h1": "Download TrueCombat: Platinum",
        "lede": "The complete game for Windows 10 and 11, free of charge. One small installer sets up the game and the launcher, then keeps both current.",
        "all": "All releases",
        "s1": "<b>Download the installer.</b> It is a small file, so it never grows with new releases.",
        "s2": "<b>Choose where to install.</b> Keep the game and the launcher together, or give each its own folder.",
        "s3": "<b>Let the launcher do the rest.</b> It downloads the game, verifies every file and keeps it current. Updates only fetch the files that changed.",
        "note": "Already installed? Open the launcher. It updates itself and the game.",
        "need": "What you need",
        "r1t": "System", "r1": "Windows 10 or 11, 64-bit",
        "r2t": "Graphics", "r2": "A DirectX 12 card. Older cards can use Safe start (OpenGL).",
        "r3": "Optional, NVIDIA RTX cards",
        "r4t": "Disk", "r4": "About 2.3 GB free space",
        "r5t": "Online", "r5": "A connection for the download and for online play. Bot matches work offline.",
        "r6t": "Price", "r6": "Free. No store, no paid unlocks.",
        "in_eyebrow": "In the download", "in_h": "Everything you need to play",
        "f1t": "The full game", "f1": "Six original maps, all 27 guns and seven game modes. There is nothing else to install: no copy of TC:E, no Enemy Territory.",
        "f2t": "The launcher", "f2": "Server browser, one-click hosting, graphics presets and a Safe start button for older hardware, all in one window.",
        "f3t": "Signed updates", "f3": "The launcher checks for new versions, fetches only the files that changed and installs only updates signed by Team Terminus.",
        "go_eyebrow": "First match", "go_h": "From install to in-game",
        "g1t": "Pick a name", "g1": "Open TrueCombat: Platinum and type your player name. It is saved for next time.",
        "g2t": "Join a server", "g2": "The Servers tab lists every public server. Official #2 always has a match running, and Official #1 counts towards the <a href=\"leaderboards.html\">leaderboards</a>.",
        "g3t": "Or warm up first", "g3": "Practice offline with bots starts a match in one click. The <a href=\"guide.html\">beginner's guide</a> covers the controls.",
        "acct": "Playing on more than one PC? A free <a href=\"account.html\">account</a> keeps your rank, stats and name with you. You sign in with Discord, and it is entirely optional.",
        "help_eyebrow": "Help", "help_h": "If something stops you",
        "h1t": "Windows shows a SmartScreen notice", "h1a": "Windows shows this for installers it has not seen often yet. Choose <b>More info</b>, then <b>Run anyway</b>. From then on the launcher verifies every update itself.",
        "h2t": "DirectX 12 won't start", "h2a": "Press <b>Safe start</b> in the launcher. It runs the game on OpenGL in a 1280 × 720 window and leaves your normal settings alone.",
        "h3t": "My server runs an older version", "h3a": "Everyone in a match needs the same version. The launcher can stay on an older release for as long as your community needs it, and return to the latest whenever you like.",
        "h4t": "I need a hand", "h4a": "Ask in the <a href=\"https://discord.gg/8kcHdg2Hch\">TrueCombat: Platinum Discord</a>. The team and the community answer there every day.",
        "help_all": "All questions and answers",
    },
    "nl": {
        "title": "Download TrueCombat: Platinum · Gratis voor Windows 10 en 11",
        "desc": "Download TrueCombat: Platinum gratis voor Windows 10 en 11. Eén klein installatieprogramma zet het volledige spel en de launcher klaar, zonder aparte installatie van TC:E of Enemy Territory.",
        "og": "Gratis download voor Windows 10 en 11. Eén klein installatieprogramma, het volledige spel, ondertekende updates.",
        "eyebrow": "Download", "h1": "Download TrueCombat: Platinum",
        "lede": "Het complete spel voor Windows 10 en 11, helemaal gratis. Eén klein installatieprogramma zet het spel en de launcher klaar en houdt beide up-to-date.",
        "all": "Alle releases",
        "s1": "<b>Download het installatieprogramma.</b> Het is een klein bestand en groeit dus niet mee met nieuwe releases.",
        "s2": "<b>Kies waar je installeert.</b> Zet het spel en de launcher bij elkaar, of geef ze elk een eigen map.",
        "s3": "<b>De launcher doet de rest.</b> Die downloadt het spel, controleert elk bestand en houdt alles up-to-date. Updates halen alleen de gewijzigde bestanden op.",
        "note": "Al geïnstalleerd? Open de launcher. Die werkt zichzelf en het spel bij.",
        "need": "Wat je nodig hebt",
        "r1t": "Systeem", "r1": "Windows 10 of 11, 64-bit",
        "r2t": "Graphics", "r2": "Een DirectX 12-kaart. Oudere kaarten kunnen Safe start gebruiken (OpenGL).",
        "r3": "Optioneel, NVIDIA RTX-kaarten",
        "r4t": "Schijf", "r4": "Ongeveer 2,3 GB vrije ruimte",
        "r5t": "Online", "r5": "Een verbinding voor de download en voor online spelen. Potjes tegen bots werken offline.",
        "r6t": "Prijs", "r6": "Gratis. Geen winkel, geen betaalde extra's.",
        "in_eyebrow": "In de download", "in_h": "Alles wat je nodig hebt om te spelen",
        "f1t": "Het volledige spel", "f1": "Zes originele maps, alle 27 wapens en zeven spelmodi. Verder hoef je niets te installeren: geen TC:E, geen Enemy Territory.",
        "f2t": "De launcher", "f2": "Serverlijst, hosten met één klik, grafische presets en een knop Safe start voor oudere hardware, allemaal in één venster.",
        "f3t": "Ondertekende updates", "f3": "De launcher controleert op nieuwe versies, haalt alleen de gewijzigde bestanden op en installeert alleen updates die door Team Terminus zijn ondertekend.",
        "go_eyebrow": "Eerste potje", "go_h": "Van installatie tot in-game",
        "g1t": "Kies een naam", "g1": "Open TrueCombat: Platinum en typ je spelersnaam. Die wordt bewaard voor de volgende keer.",
        "g2t": "Kies een server", "g2": "Het tabblad Servers toont elke publieke server. Op Official #2 loopt altijd een potje, en Official #1 telt mee voor de <a href=\"leaderboards.html\">ranglijsten</a>.",
        "g3t": "Of speel je eerst warm", "g3": "Practice offline with bots start met één klik een potje. De <a href=\"guide.html\">beginnersgids</a> legt de besturing uit.",
        "acct": "Speel je op meer dan één pc? Met een gratis <a href=\"account.html\">account</a> neem je je rang, statistieken en naam overal mee. Je meldt je aan met Discord, en het is helemaal optioneel.",
        "help_eyebrow": "Hulp", "help_h": "Als iets je tegenhoudt",
        "h1t": "Windows toont een SmartScreen-melding", "h1a": "Windows toont die bij installatieprogramma's die het nog niet vaak heeft gezien. Kies <b>Meer informatie</b> en daarna <b>Toch uitvoeren</b>. Vanaf dan controleert de launcher elke update zelf.",
        "h2t": "DirectX 12 start niet", "h2a": "Druk op <b>Safe start</b> in de launcher. Het spel draait dan op OpenGL in een venster van 1280 × 720 en je gewone instellingen blijven ongemoeid.",
        "h3t": "Mijn server draait een oudere versie", "h3a": "Iedereen in een potje heeft dezelfde versie nodig. De launcher kan op een oudere release blijven zolang je community dat nodig heeft, en je gaat terug naar de nieuwste wanneer je wilt.",
        "h4t": "Ik kom er niet uit", "h4a": "Vraag het in de <a href=\"https://discord.gg/8kcHdg2Hch\">TrueCombat: Platinum-Discord</a>. Het team en de community helpen je daar elke dag verder.",
        "help_all": "Alle vragen en antwoorden",
    },
}

# ---------------------------------------------------------------- FAQ
# (group id, group title, [(question id, question, answer html)])
FAQ = {
    "en": {
        "title": "FAQ: install, online play and graphics · TrueCombat: Platinum",
        "desc": "Answers about TrueCombat: Platinum: what it is, how to install it, system requirements, online play, servers, leaderboards, graphics settings and how it relates to TrueCombat: Elite.",
        "og": "What it is, how to install it, online play, graphics and how it relates to TrueCombat: Elite.",
        "eyebrow": "Questions", "h1": "Questions and answers",
        "lede": "Everything players ask before their first match, and a few things they ask after it.",
        "toc": "On this page",
        "more_h": "Still stuck?", "more": "Ask in the <a href=\"https://discord.gg/8kcHdg2Hch\">TrueCombat: Platinum Discord</a>. The team reads every question.",
        "groups": [
            ("start", "Getting started", [
                ("what", "What is TrueCombat: Platinum?", "A native 64-bit Windows rebuild of <a href=\"truecombat-elite.html\">TrueCombat: Elite</a>, the realistic modern-combat total conversion for Enemy Territory. It has a DirectX 12 renderer, the original maps, soldiers and HUD, and a launcher that hosts servers and installs signed updates."),
                ("free", "Is it free?", "Yes. There is no store and nothing to unlock with money, and every weapon is available from your first match. <a href=\"download.html\">Download it</a> and play."),
                ("need-tce", "Do I need TrueCombat: Elite or Enemy Territory installed?", "No. The download contains everything needed to play."),
                ("requirements", "What do I need to run it?", "Windows 10 or 11, 64-bit, a DirectX 12 graphics card and about 2.3 GB of free disk space. Older cards can use Safe start, which runs the game on OpenGL."),
                ("install", "How do I install it?", "Download the installer from the <a href=\"download.html\">download page</a>, choose a folder and let the launcher fetch the game. After that the launcher keeps the game and itself current."),
                ("new", "I'm new. Where do I start?", "Read the <a href=\"guide.html\">beginner's guide</a> for the controls, game modes and a few tips that keep you alive longer. The <a href=\"weapons.html\">weapons page</a> lists every gun, and the <a href=\"maps.html\">maps page</a> has an overhead layout of every map."),
            ]),
            ("online", "Playing online", [
                ("servers", "Can I play online?", "Yes. Two official EU servers run around the clock: Official #1 is ranked, and Official #2 is unranked with bots filling the empty slots. Both are in the launcher's Servers tab, next to every other <a href=\"servers.html\">public server</a>."),
                ("host", "Can I host my own server?", "Yes. Press <b>Host a server</b> in the launcher and pick the mode, map rotation and player limit. Switch on <b>List publicly</b> to appear on the server list. Players outside your home network need UDP port 27971 forwarded to the hosting PC."),
                ("ranked", "How do the leaderboards work?", "Every completed match on a ranked server counts towards your rank and rating. You appear on the <a href=\"leaderboards.html\">leaderboards</a> after your first completed match, and each player gets a profile page with weapons, recent matches and rating history."),
                ("match-mode", "Is there a mode for clan matches?", "Yes. <a href=\"competitive.html\">Match mode</a> adds ready-up, a knife round for sides, half-time and tactical timeouts that freeze the whole match. It is built into every server."),
                ("offline", "Can I play offline?", "Yes. <b>Practice offline with bots</b> in the launcher starts a match in one click, with no connection needed."),
                ("players", "Where do I find players?", "Join the <a href=\"https://discord.gg/8kcHdg2Hch\">TrueCombat: Platinum Discord</a>. That's where matches get organised, servers get shared and new versions are announced first."),
            ]),
            ("graphics", "Graphics and performance", [
                ("dx12", "DirectX 12 won't start. What now?", "Press <b>Safe start</b> in the launcher. It runs the game on OpenGL in a 1280 × 720 window, and the game also falls back to OpenGL by itself if DirectX 12 fails."),
                ("presets", "Can I keep the original look?", "Yes. The Low preset is the original look, with stock filtering and no added effects. High is the default, and Ultra adds modern lighting and real-time sun shadows. You can switch at any time from the launcher."),
                ("dlss", "Does it support DLSS?", "Yes. NVIDIA DLSS and DLAA are optional on RTX cards. Everything else runs on any DirectX 12 card."),
                ("ultrawide", "Does it support ultrawide monitors?", "Yes. The field of view widens on 21:9 and 32:9 screens instead of cropping, and the HUD stays centred."),
                ("linux", "Is there a Linux version?", "The dedicated server runs natively on Linux, and both official servers use it. The game itself is for Windows."),
            ]),
            ("project", "The project", [
                ("complete", "Is this complete TC:E?", "Yes, and more. Every weapon, all seven game modes, the original movement speed, leaning, ladders, swimming, ledge climbing and the sniper scope are in, joined by additions such as the live minimap and a competitive match mode. The <a href=\"./#roadmap\">roadmap</a> shows what is playable now and what follows."),
                ("official", "Is it an official TrueCombat release?", "No. TrueCombat: Elite was created by Team Terminator. TrueCombat: Platinum is a fan project by Team Terminus and is not affiliated with or endorsed by the original team."),
                ("who", "Who makes it?", "<a href=\"studio.html\">Team Terminus</a>: two TrueCombat: Elite veterans. RaziC* leads development and RavoC leads the community."),
                ("follow", "How do I follow development?", "The <a href=\"devlog.html\">devlog</a> explains what is being built and why, the <a href=\"news.html\">patch notes</a> list every change, and new versions are announced on Discord first."),
                ("support", "How can I support the project?", "Playing and bringing a friend helps most. If you want to chip in towards the servers, the <a href=\"support.html\">support page</a> shows where every euro goes. Nothing in the game is sold."),
                ("press", "I want to write about it", "Grab the <a href=\"press.html\">press kit</a> with logos, unedited screenshots and a fact sheet."),
            ]),
        ],
    },
    "nl": {
        "title": "Veelgestelde vragen: installeren, online spelen en graphics · TrueCombat: Platinum",
        "desc": "Antwoorden over TrueCombat: Platinum: wat het is, hoe je het installeert, systeemeisen, online spelen, servers, ranglijsten, grafische instellingen en de band met TrueCombat: Elite.",
        "og": "Wat het is, hoe je het installeert, online spelen, graphics en de band met TrueCombat: Elite.",
        "eyebrow": "Vragen", "h1": "Vragen en antwoorden",
        "lede": "Alles wat spelers vragen voor hun eerste potje, en een paar dingen die ze daarna vragen.",
        "toc": "Op deze pagina",
        "more_h": "Kom je er niet uit?", "more": "Vraag het in de <a href=\"https://discord.gg/8kcHdg2Hch\">TrueCombat: Platinum-Discord</a>. Het team leest elke vraag.",
        "groups": [
            ("start", "Aan de slag", [
                ("what", "Wat is TrueCombat: Platinum?", "Een native 64-bit Windows-versie van <a href=\"truecombat-elite.html\">TrueCombat: Elite</a>, de realistische total conversion voor Enemy Territory in een moderne setting. Met een DirectX 12-renderer, de originele maps, soldaten en HUD, en een launcher die servers host en ondertekende updates installeert."),
                ("free", "Is het gratis?", "Ja. Er is geen winkel en niets dat je met geld vrijspeelt, en elk wapen is vanaf je eerste potje beschikbaar. <a href=\"download.html\">Download het</a> en speel."),
                ("need-tce", "Moet ik TrueCombat: Elite of Enemy Territory geïnstalleerd hebben?", "Nee. In de download zit alles wat je nodig hebt om te spelen."),
                ("requirements", "Wat heb ik nodig om het te draaien?", "Windows 10 of 11, 64-bit, een DirectX 12-videokaart en ongeveer 2,3 GB vrije schijfruimte. Oudere kaarten kunnen Safe start gebruiken, dat het spel op OpenGL draait."),
                ("install", "Hoe installeer ik het?", "Download het installatieprogramma van de <a href=\"download.html\">downloadpagina</a>, kies een map en laat de launcher het spel ophalen. Daarna houdt de launcher het spel en zichzelf up-to-date."),
                ("new", "Ik ben nieuw. Waar begin ik?", "Lees de <a href=\"guide.html\">beginnersgids</a> voor de besturing, de spelmodi en een paar tips waarmee je langer overleeft. De <a href=\"weapons.html\">wapenpagina</a> toont elk wapen, en op de <a href=\"maps.html\">mappagina</a> staat van elke map een plattegrond."),
            ]),
            ("online", "Online spelen", [
                ("servers", "Kan ik online spelen?", "Ja. Twee officiële EU-servers draaien dag en nacht: Official #1 is ranked, en Official #2 is unranked met bots op de lege plekken. Beide staan in het tabblad Servers van de launcher, naast elke andere <a href=\"servers.html\">publieke server</a>."),
                ("host", "Kan ik zelf een server hosten?", "Ja. Druk in de launcher op <b>Host a server</b> en kies de modus, de maprotatie en het spelerslimiet. Zet <b>List publicly</b> aan om op de serverlijst te verschijnen. Voor spelers buiten je thuisnetwerk moet UDP-poort 27971 naar de hostende pc zijn doorgestuurd."),
                ("ranked", "Hoe werken de ranglijsten?", "Elk uitgespeeld potje op een ranked server telt mee voor je rang en rating. Je verschijnt op de <a href=\"leaderboards.html\">ranglijsten</a> na je eerste uitgespeelde potje, en elke speler krijgt een profielpagina met wapens, recente potjes en ratingverloop."),
                ("match-mode", "Is er een modus voor clanwedstrijden?", "Ja. De <a href=\"competitive.html\">wedstrijdmodus</a> voegt ready-up, een mesronde om de kant, een rust en tactische time-outs toe die de hele wedstrijd bevriezen. Hij zit in elke server ingebouwd."),
                ("offline", "Kan ik offline spelen?", "Ja. <b>Practice offline with bots</b> in de launcher start met één klik een potje, zonder verbinding."),
                ("players", "Waar vind ik spelers?", "Word lid van de <a href=\"https://discord.gg/8kcHdg2Hch\">TrueCombat: Platinum-Discord</a>. Daar worden potjes afgesproken, servers gedeeld en nieuwe versies als eerste aangekondigd."),
            ]),
            ("graphics", "Graphics en prestaties", [
                ("dx12", "DirectX 12 start niet. Wat nu?", "Druk op <b>Safe start</b> in de launcher. Het spel draait dan op OpenGL in een venster van 1280 × 720, en het spel valt ook zelf terug op OpenGL als DirectX 12 niet werkt."),
                ("presets", "Kan ik de originele look houden?", "Ja. De preset Low is de originele look, met de standaardfiltering en zonder extra effecten. High is de standaard, en Ultra voegt moderne belichting en realtime zonschaduwen toe. Je wisselt wanneer je wilt in de launcher."),
                ("dlss", "Ondersteunt het DLSS?", "Ja. NVIDIA DLSS en DLAA zijn optioneel op RTX-kaarten. Al het andere draait op elke DirectX 12-kaart."),
                ("ultrawide", "Ondersteunt het ultrawide-schermen?", "Ja. Op 21:9- en 32:9-schermen wordt het gezichtsveld breder in plaats van afgesneden, en de HUD blijft in het midden."),
                ("linux", "Is er een Linux-versie?", "De dedicated server draait native op Linux, en beide officiële servers gebruiken die. Het spel zelf is voor Windows."),
            ]),
            ("project", "Het project", [
                ("complete", "Is dit de complete TC:E?", "Ja, en meer. Elk wapen, alle zeven spelmodi, de originele bewegingssnelheid, leunen, ladders, zwemmen, klimmen op randen en het sluipschuttersvizier zitten erin, aangevuld met nieuwe onderdelen zoals de live minimap en een competitieve wedstrijdmodus. De <a href=\"./#roadmap\">roadmap</a> toont wat nu speelbaar is en wat volgt."),
                ("official", "Is dit een officiële TrueCombat-release?", "Nee. TrueCombat: Elite is gemaakt door Team Terminator. TrueCombat: Platinum is een fanproject van Team Terminus en is niet verbonden aan of goedgekeurd door het oorspronkelijke team."),
                ("who", "Wie maakt het?", "<a href=\"studio.html\">Team Terminus</a>: twee TrueCombat: Elite-veteranen. RaziC* leidt de ontwikkeling en RavoC de community."),
                ("follow", "Hoe volg ik de ontwikkeling?", "De <a href=\"devlog.html\">devlog</a> legt uit wat er gebouwd wordt en waarom, de <a href=\"news.html\">patchnotes</a> tonen elke wijziging, en nieuwe versies worden als eerste op Discord aangekondigd."),
                ("support", "Hoe kan ik het project steunen?", "Spelen en een vriend meenemen helpt het meest. Wil je bijdragen aan de servers, dan toont de <a href=\"support.html\">steunpagina</a> waar elke euro naartoe gaat. In het spel wordt niets verkocht."),
                ("press", "Ik wil erover schrijven", "Download de <a href=\"press.html\">perskit</a> met logo's, onbewerkte screenshots en een factsheet."),
            ]),
        ],
    },
}

# ---------------------------------------------------------------- TrueCombat: Elite
ELITE = """<section class="page-head">
  <div class="head-art" style="--art: url({{up}}img/map-delta.webp); --art-s: url({{up}}img/map-delta-640.webp)" aria-hidden="true"></div>
  <div class="wrap">
    <span class="eyebrow">TrueCombat: Elite</span>
    <h1>[[h1]]</h1>
    <p class="lede">[[lede]]</p>
    <div class="hero-cta">
      <a class="btn btn-play" href="download.html">""" + DOWNLOAD_SVG + """<span class="stack"><span class="big">Download {{version}}</span><span class="small">[[cta_small]]</span></span></a>
      <a class="btn btn-ghost" href="maps.html">[[cta_maps]]</a>
    </div>
  </div>
</section>

<section class="band">
  <div class="wrap doc">
    <nav class="doc-toc" aria-label="[[toc]]">
      <a href="#original">[[n1]]</a><a href="#today">[[n2]]</a><a href="#platinum">[[n3]]</a><a href="#compare">[[n4]]</a><a href="#return">[[n5]]</a>
    </nav>
    <div class="doc-body">
      <section id="original">
        <span class="eyebrow">01</span>
        <h2>[[o_h]]</h2>
        <p>[[o1]]</p>
        <p>[[o2]]</p>
      </section>

      <section id="today">
        <span class="eyebrow">02</span>
        <h2>[[t_h]]</h2>
        <p>[[t1]]</p>
        <p>[[t2]]</p>
      </section>

      <section id="platinum">
        <span class="eyebrow">03</span>
        <h2>[[p_h]]</h2>
        <p>[[p1]]</p>
        <ul>
          <li>[[p_a]]</li>
          <li>[[p_b]]</li>
          <li>[[p_c]]</li>
          <li>[[p_d]]</li>
        </ul>
        <figure class="shot-wide"><img src="{{up}}img/shot-railhouse-boxcar.webp" srcset="{{up}}img/shot-railhouse-boxcar-640.webp 640w, {{up}}img/shot-railhouse-boxcar.webp 1280w, {{up}}img/shot-railhouse-boxcar-1920.webp 1920w" sizes="(max-width: 900px) 92vw, 760px" alt="[[fig_alt]]" width="1280" height="720" loading="lazy"><figcaption>[[fig]]</figcaption></figure>
      </section>

      <section id="compare">
        <span class="eyebrow">04</span>
        <h2>[[c_h]]</h2>
        <div class="vs-scroll">
          <table class="vs">
            <thead><tr><td></td><th scope="col">[[c_orig]]</th><th scope="col">TrueCombat: Platinum</th></tr></thead>
            <tbody>
[[rows]]
            </tbody>
          </table>
        </div>
      </section>

      <section id="return">
        <span class="eyebrow">05</span>
        <h2>[[r_h]]</h2>
        <p>[[r1]]</p>
        <ol>
          <li>[[r_a]]</li>
          <li>[[r_b]]</li>
          <li>[[r_c]]</li>
        </ol>
        <p class="callout">[[r_note]]</p>
      </section>
    </div>
  </div>
</section>
"""

ELITE_T = {
    "en": {
        "title": "TrueCombat: Elite in 2026 · Play TC:E on Windows 10 and 11",
        "desc": "TrueCombat: Elite (TC:E) was the realistic tactical shooter built on Enemy Territory. TrueCombat: Platinum brings its maps, weapons and movement to Windows 10 and 11 as a free 64-bit game.",
        "og": "The realistic tactical shooter built on Enemy Territory, playable today on Windows 10 and 11.",
        "h1": "TrueCombat: Elite, playable today",
        "lede": "TC:E was one of the most demanding tactical shooters of its time. TrueCombat: Platinum brings it to modern Windows as a free 64-bit game, with the maps, weapons and movement you remember.",
        "cta_small": "Free for Windows 10 and 11", "cta_maps": "See the maps",
        "toc": "On this page", "n1": "The original", "n2": "TC:E today", "n3": "Platinum", "n4": "Side by side", "n5": "Coming back",
        "o_h": "What TrueCombat: Elite was",
        "o1": "<b>TrueCombat: Elite</b>, TC:E for short, is a free total conversion for Wolfenstein: Enemy Territory, made by Team Terminator. It followed the original TrueCombat for Quake III Arena and swapped the engine's Second World War for modern combat.",
        "o2": "It played like nothing else on that engine. One life per round. Iron sights and real weapon handling. Stamina that punished careless sprinting, leaning around corners, and maps built for slow, deliberate play. A single mistake ended your round, and that is exactly why people stayed for years.",
        "t_h": "Why TC:E is hard to play today",
        "t1": "The original still runs, but it shows its age. It is a 32-bit mod on an engine from 2003, it needs a separate Enemy Territory install, and it has no installer or updater of its own.",
        "t2": "The bigger problem is finding a match. Most of the public servers that carried the community have gone quiet, and a returning player has no obvious place to start.",
        "p_h": "What TrueCombat: Platinum is",
        "p1": "Platinum rebuilds TC:E as a native 64-bit Windows game with a DirectX 12 renderer. The aim is simple: everything that was in TC:E should look, sound and handle the way you remember it.",
        "p_a": "<b>The original maps, soldiers and HUD.</b> The HUD is matched against the original pixel by pixel.",
        "p_b": "<b>The original movement.</b> Sprint, run, crouch and prone speeds come straight from the TC:E values, with leaning, ladders and swimming.",
        "p_c": "<b>The full arsenal.</b> All 27 guns, the knife and every grenade, with the original damage, recoil and spread.",
        "p_d": "<b>All seven game modes</b>, from Elimination to Bomb and Flag Capture.",
        "fig_alt": "The TrueCombat: Platinum HUD during a live round on Railhouse: score, round timer, compass, objective, health and ammo",
        "fig": "The HUD in a live round on Railhouse, rendered in DirectX 12.",
        "c_h": "Original and Platinum, side by side", "c_orig": "TrueCombat: Elite",
        "rows": [
            ("Platform", "32-bit mod for Wolfenstein: Enemy Territory", "Native 64-bit Windows game, nothing else to install"),
            ("Renderer", "OpenGL, on an engine from 2003", "DirectX 12 with OpenGL fallback, optional NVIDIA DLSS / DLAA"),
            ("Look", "The original", "The original on the Low preset, or modern lighting and real-time sun shadows on Ultra"),
            ("Install", "Enemy Territory plus the mod files", "One small installer"),
            ("Updates", "Manual downloads", "Signed updates through the launcher"),
            ("Servers", "Community servers, few still online", "Two official EU servers around the clock, a public server list and one-click hosting"),
            ("Rankings", "None built in", "Leaderboards and player profiles from every ranked match"),
            ("Clan matches", "Arranged by hand", "Match mode with ready-up, knife round, half-time and timeouts"),
            ("Screens", "Custom resolutions through console commands", "Any resolution, with a wider field of view on 21:9 and 32:9"),
            ("Price", "Free", "Free"),
        ],
        "r_h": "Coming back after a few years",
        "r1": "If you played TC:E, you already know how to play Platinum. The keys, the pace and the maps are where you left them.",
        "r_a": "<a href=\"download.html\">Download the installer</a> and let the launcher set up the game.",
        "r_b": "Join <b>Official #2</b> from the Servers tab to shake off the rust, then move to <b>Official #1</b> when you want your matches to count.",
        "r_c": "Say hello on the <a href=\"https://discord.gg/8kcHdg2Hch\">Discord</a>. Veterans and new players set up their matches there.",
        "r_note": "<b>New to TC:E?</b> The <a href=\"guide.html\">beginner's guide</a> covers the controls, the game modes and the habits that keep you alive.",
    },
    "nl": {
        "title": "TrueCombat: Elite in 2026 · Speel TC:E op Windows 10 en 11",
        "desc": "TrueCombat: Elite (TC:E) was de realistische tactische shooter op basis van Enemy Territory. TrueCombat: Platinum brengt de maps, wapens en beweging naar Windows 10 en 11 als gratis 64-bit game.",
        "og": "De realistische tactische shooter op basis van Enemy Territory, vandaag speelbaar op Windows 10 en 11.",
        "h1": "TrueCombat: Elite, vandaag speelbaar",
        "lede": "TC:E was een van de veeleisendste tactische shooters van zijn tijd. TrueCombat: Platinum brengt het naar modern Windows als gratis 64-bit game, met de maps, wapens en beweging die je kent.",
        "cta_small": "Gratis voor Windows 10 en 11", "cta_maps": "Bekijk de maps",
        "toc": "Op deze pagina", "n1": "Het origineel", "n2": "TC:E vandaag", "n3": "Platinum", "n4": "Naast elkaar", "n5": "Terugkomen",
        "o_h": "Wat TrueCombat: Elite was",
        "o1": "<b>TrueCombat: Elite</b>, kortweg TC:E, is een gratis total conversion voor Wolfenstein: Enemy Territory, gemaakt door Team Terminator. Het volgde op het oorspronkelijke TrueCombat voor Quake III Arena en ruilde de Tweede Wereldoorlog van de engine in voor een moderne setting.",
        "o2": "Het speelde als niets anders op die engine. Eén leven per ronde. Richten over het vizier en echte wapenbeheersing. Uithoudingsvermogen dat roekeloos sprinten afstrafte, leunen om hoeken, en maps gemaakt voor rustig, doordacht spel. Eén fout en je ronde was voorbij, en precies daarom bleven spelers jarenlang.",
        "t_h": "Waarom TC:E vandaag lastig te spelen is",
        "t1": "Het origineel draait nog, maar je merkt de leeftijd. Het is een 32-bit mod op een engine uit 2003, het heeft een aparte installatie van Enemy Territory nodig en het heeft geen eigen installatieprogramma of updater.",
        "t2": "Het grotere probleem is een potje vinden. De meeste publieke servers waar de community op draaide zijn stilgevallen, en wie terugkomt heeft geen duidelijke plek om te beginnen.",
        "p_h": "Wat TrueCombat: Platinum is",
        "p1": "Platinum bouwt TC:E opnieuw als native 64-bit Windows-game met een DirectX 12-renderer. Het doel is eenvoudig: alles wat in TC:E zat moet eruitzien, klinken en aanvoelen zoals je het kent.",
        "p_a": "<b>De originele maps, soldaten en HUD.</b> De HUD is pixel voor pixel met het origineel vergeleken.",
        "p_b": "<b>De originele beweging.</b> De snelheden voor sprinten, rennen, hurken en liggen komen rechtstreeks uit de TC:E-waarden, met leunen, ladders en zwemmen.",
        "p_c": "<b>Het volledige arsenaal.</b> Alle 27 wapens, het mes en elke granaat, met de originele schade, terugslag en spreiding.",
        "p_d": "<b>Alle zeven spelmodi</b>, van Elimination tot Bomb en Flag Capture.",
        "fig_alt": "De HUD van TrueCombat: Platinum tijdens een ronde op Railhouse: score, rondetimer, kompas, doel, gezondheid en munitie",
        "fig": "De HUD tijdens een ronde op Railhouse, gerenderd in DirectX 12.",
        "c_h": "Origineel en Platinum, naast elkaar", "c_orig": "TrueCombat: Elite",
        "rows": [
            ("Platform", "32-bit mod voor Wolfenstein: Enemy Territory", "Native 64-bit Windows-game, verder niets te installeren"),
            ("Renderer", "OpenGL, op een engine uit 2003", "DirectX 12 met OpenGL als terugval, optioneel NVIDIA DLSS / DLAA"),
            ("Look", "Het origineel", "Het origineel op de preset Low, of moderne belichting en realtime zonschaduwen op Ultra"),
            ("Installatie", "Enemy Territory plus de modbestanden", "Eén klein installatieprogramma"),
            ("Updates", "Handmatige downloads", "Ondertekende updates via de launcher"),
            ("Servers", "Communityservers, waarvan nog weinig online", "Twee officiële EU-servers dag en nacht, een publieke serverlijst en hosten met één klik"),
            ("Ranglijsten", "Niet ingebouwd", "Ranglijsten en spelersprofielen uit elk ranked potje"),
            ("Clanwedstrijden", "Met de hand geregeld", "Wedstrijdmodus met ready-up, mesronde, rust en time-outs"),
            ("Schermen", "Eigen resoluties via consolecommando's", "Elke resolutie, met een breder gezichtsveld op 21:9 en 32:9"),
            ("Prijs", "Gratis", "Gratis"),
        ],
        "r_h": "Terugkomen na een paar jaar",
        "r1": "Als je TC:E hebt gespeeld, kun je Platinum al spelen. De toetsen, het tempo en de maps zijn waar je ze hebt achtergelaten.",
        "r_a": "<a href=\"download.html\">Download het installatieprogramma</a> en laat de launcher het spel klaarzetten.",
        "r_b": "Speel eerst op <b>Official #2</b> via het tabblad Servers om er weer in te komen, en stap over naar <b>Official #1</b> wanneer je potjes moeten meetellen.",
        "r_c": "Zeg hallo op de <a href=\"https://discord.gg/8kcHdg2Hch\">Discord</a>. Veteranen en nieuwe spelers spreken daar hun potjes af.",
        "r_note": "<b>Nieuw met TC:E?</b> De <a href=\"guide.html\">beginnersgids</a> behandelt de besturing, de spelmodi en de gewoontes waarmee je overleeft.",
    },
}


# ---------------------------------------------------------------- privacy
PRIVACY = """<section class="page-head">
  <div class="head-art" style="--art: url({{up}}img/map-stadtrand.webp); --art-s: url({{up}}img/map-stadtrand-640.webp)" aria-hidden="true"></div>
  <div class="wrap">
    <span class="eyebrow">[[eyebrow]]</span>
    <h1>[[h1]]</h1>
    <p class="lede">[[lede]]</p>
  </div>
</section>

<section class="band">
  <div class="wrap doc">
    <nav class="doc-toc" aria-label="[[toc]]">
      <a href="#short">[[n1]]</a><a href="#website">[[n2]]</a><a href="#game">[[n3]]</a><a href="#launcher">[[n6]]</a><a href="#accounts">[[n7]]</a><a href="#community">[[n8]]</a><a href="#partners">[[n9]]</a><a href="#choices">[[n4]]</a><a href="#changes">[[n5]]</a>
    </nav>
    <div class="doc-body">
      <section id="short">
        <span class="eyebrow">01</span>
        <h2>[[s_h]]</h2>
        <ul>
          <li>[[s_a]]</li>
          <li>[[s_b]]</li>
          <li>[[s_c]]</li>
          <li>[[s_d]]</li>
          <li>[[s_e]]</li>
        </ul>
      </section>

      <section id="website">
        <span class="eyebrow">02</span>
        <h2>[[w_h]]</h2>
        <p>[[w1]]</p>
        <p>[[w2]]</p>
        <p>[[w3]]</p>
        <h3>[[w_keep_h]]</h3>
        <p>[[w_keep]]</p>
        <h3>[[w_never_h]]</h3>
        <ul>
          <li>[[w_n1]]</li>
          <li>[[w_n2]]</li>
          <li>[[w_n3]]</li>
          <li>[[w_n4]]</li>
        </ul>
        <p>[[w4]]</p>
        <p>[[w5]]</p>
      </section>

      <section id="game">
        <span class="eyebrow">03</span>
        <h2>[[g_h]]</h2>
        <ul>
          <li>[[g_a]]</li>
          <li>[[g_b]]</li>
          <li>[[g_c]]</li>
          <li>[[g_d]]</li>
          <li>[[g_e]]</li>
          <li>[[g_f]]</li>
        </ul>
      </section>

      <section id="launcher">
        <span class="eyebrow">04</span>
        <h2>[[l_h]]</h2>
        <p>[[l1]]</p>
        <p>[[l2]]</p>
        <ul>
          <li>[[l_a]]</li>
          <li>[[l_b]]</li>
          <li>[[l_c]]</li>
        </ul>
        <p>[[l3]]</p>
        <p>[[l4]]</p>
        <p class="callout">[[g_note]]</p>
      </section>

      <section id="accounts">
        <span class="eyebrow">05</span>
        <h2>[[a_h]]</h2>
        <p>[[a1]]</p>
        <ul>
          <li>[[a_a]]</li>
          <li>[[a_b]]</li>
          <li>[[a_c]]</li>
        </ul>
        <p>[[a2]]</p>
      </section>

      <section id="community">
        <span class="eyebrow">06</span>
        <h2>[[m_h]]</h2>
        <ul>
          <li>[[m_a]]</li>
          <li>[[m_b]]</li>
          <li>[[m_c]]</li>
        </ul>
      </section>

      <section id="partners">
        <span class="eyebrow">07</span>
        <h2>[[p_h]]</h2>
        <p>[[p1]]</p>
        <ul>
          <li>[[p_a]]</li>
          <li>[[p_b]]</li>
          <li>[[p_c]]</li>
          <li>[[p_d]]</li>
          <li>[[p_e]]</li>
        </ul>
        <p>[[p2]]</p>
      </section>

      <section id="choices">
        <span class="eyebrow">08</span>
        <h2>[[c_h]]</h2>
        <p>[[c1]]</p>
        <p>[[c2]]</p>
        <p>[[c3]]</p>
      </section>

      <section id="changes">
        <span class="eyebrow">09</span>
        <h2>[[x_h]]</h2>
        <p>[[x1]]</p>
        <p class="yt-note">[[credit]]</p>
      </section>
    </div>
  </div>
</section>
"""

PRIVACY_T = {
    "en": {
        "title": "Privacy · TrueCombat: Platinum",
        "desc": "What the TrueCombat: Platinum website, launcher and servers collect, what they never collect, and how to opt out. No cookies, no ad trackers, no analytics companies.",
        "og": "No cookies, no ad trackers, no analytics companies. Here is exactly what we count.",
        "eyebrow": "Privacy", "h1": "What we count, and what we never will",
        "lede": "We want to know which pages are worth reading and where new players hear about the game. We do not need to know who you are to find that out, so we never ask.",
        "toc": "On this page", "n1": "The short version", "n2": "This website", "n3": "The game", "n4": "Your rights", "n5": "Changes",
        "s_h": "The short version",
        "s_a": "<b>No tracking cookies, no ad trackers, no analytics companies.</b> Nothing from Google, Meta or anyone else is loaded on this site.",
        "s_b": "<b>We count visits, not visitors.</b> The website keeps daily totals and nothing that points back to a person.",
        "s_c": "<b>Your browser says no, we listen.</b> With Global Privacy Control or Do Not Track switched on, you are not counted at all.",
        "s_d": "<b>The launcher shares crash and hardware data only if you say yes.</b> It asks once, with two equal buttons, and you can change your answer at any time.",
        "w_h": "This website",
        "w1": "When a page opens, your browser sends one short message to our own server: the page, the site that linked you here (the site name only, never the full address), the campaign tag in the link if there is one, the page language, and whether the screen is a phone, tablet or desktop size. A click on a download button sends one more message saying a download started.",
        "w2": "To count you once per day instead of on every page, the server makes a one-way fingerprint from your connection address and browser, mixed with a random secret that only exists for that day. The same fingerprint lets a download count toward the site that brought you here that day. At midnight UTC the secret and every fingerprint are deleted. After that, nobody can connect one day to the next, including us.",
        "w3": "The server looks up the country of your connection address in a list it keeps on the box itself, keeps the two-letter country code and forgets the address. No outside service is asked.",
        "w_keep_h": "What we keep",
        "w_keep": "Daily totals per page, linking site, campaign, country, screen size and language, and how many of those visits led to a download. Devlog posts also keep how many people read and finished them, and their star ratings. These totals are kept for as long as the site exists.",
        "w_never_h": "What we never keep",
        "w_n1": "Connection (IP) addresses, browser details or device information",
        "w_n2": "Cookies, or anything else stored in your browser for counting",
        "w_n3": "Full addresses of the pages that sent you here",
        "w_n4": "Anything that links one visit, rating or download to a person",
        "w4": "Your browser keeps a few small notes for the site itself, never for counting: your devlog star ratings, which devlog posts you have already seen, a short-lived copy of the release notes and, while you link a PC to your account, the one-time link code. Clearing your browser data removes them.",
        "w5": "Live data such as servers and leaderboards comes from <code>api.truecombat.eu</code>, and release notes are copied onto this site, so your browser never asks GitHub for them. The site is delivered through Cloudflare, which keeps it fast and shields it from attacks. The trailer comes from YouTube only after you click play, and downloads come from GitHub. Like any web server, each of these sees your connection address while it answers.",
        "g_h": "The game and the launcher",
        "g_a": "<b>Online play.</b> Game servers see your connection address, as every online game does. Our moderation tools keep it for up to 90 days to deal with cheating and abuse, and a ban record keeps the address that was banned.",
        "g_b": "<b>Leaderboards.</b> Ranked matches on official and verified servers record your in-game name, a player ID made from your game key, and your match statistics. That is what fills the leaderboards and your public profile, and the records are kept for as long as the leaderboards exist, because every rank is built from them. Each match also keeps a one-way code of your connection address, so two players on one connection never count against each other; after 90 days that code is removed. Account holders can hide their profile at any time. Without an account, write to us and we take your name off the public pages.",
        "g_c": "<b>Anti-cheat.</b> Official servers use Easy Anti-Cheat, which runs under the <a href=\"https://www.epicgames.com/site/privacypolicy\">Epic Games privacy policy</a>.",
        "g_d": "<b>Crash reports and memory dumps</b> stay on your PC. They only reach us if you attach them to a bug report yourself. If you choose to share launcher data, only the crash location is sent, as described below.",
        "g_e": "<b>Bug reports</b> you send from the game include what you write, a screenshot and technical details such as the map, frame rate and graphics card, so we can reproduce the problem. A report and its screenshot are deleted 90 days after the issue is closed.",
        "g_note": "<b>See it for yourself.</b> Settings &gt; Privacy &gt; What is shared in the launcher shows the exact report your PC would send next, before it leaves your computer.",
        "c_h": "Your choices and rights",
        "c1": "To stop being counted on this website, switch on Global Privacy Control or Do Not Track in your browser. Blocking <code>api.truecombat.eu/insights</code> works too, and the site keeps working exactly the same.",
        "c2": "<b>Your rights.</b> You can ask for a copy of your data, have it corrected or deleted, restrict how we use it, or receive it in a portable form. You can also object to anything we do on the basis of legitimate interest. Account holders can download or delete everything themselves on the account page. For anything else, write to <a href=\"mailto:gianni@truecombat.eu\">gianni@truecombat.eu</a>. We reply within one month, and may ask you to show the data is yours, for example by writing from the account in question. All of the counting code is in the <a href=\"https://github.com/Annoximeme/TrueCombat-Platinum\">public repository</a>, so you never have to take our word for it.",
        "c3": "<b>Who is responsible.</b> TrueCombat: Platinum is made by Team Terminus. The data controller is Gianni Goossens (RaziC*), based in Belgium and reachable at <a href=\"mailto:gianni@truecombat.eu\">gianni@truecombat.eu</a>. Website counting, protecting the game servers, moderation, leaderboards and backups rest on our legitimate interest in running a fair, secure game that works (GDPR Article 6(1)(f)), with the safeguards described here. Accounts rest on your request for one (Article 6(1)(b)). Launcher data and bug reports are only sent with your consent (Article 6(1)(a)), which you can withdraw at any time. If you believe we handle your data wrongly, you can complain to a data protection authority; in Belgium, that is the <a href=\"https://www.dataprotectionauthority.be\">Data Protection Authority</a>.",
        "n6": "The launcher",
        "l_h": "Crash and hardware data from the launcher",
        "l1": "From launcher 2.6.0, the Play page asks once whether you want to share anonymous crash and hardware data. Nothing is sent until you choose Share, and nothing at all if you choose No thanks. The same switch is in Settings &gt; Privacy, and turning it off stops sharing straight away.",
        "l2": "When sharing is on, the launcher sends at most one short report a day to <code>api.truecombat.eu</code>, and only when there is something new to report:",
        "l_a": "<b>Crashes.</b> For each new crash: whether the game or the server crashed, the Windows error code, the place in the program where it happened (a file name and a position in it, such as <code>renderer_dx12_x64.dll+0x1a2b3</code>), up to five steps leading to it in the same form, and how many minutes the game had been running. Crash reports and memory dumps themselves stay on your PC.",
        "l_b": "<b>Game starts.</b> How many times the game was started since the last report, how many of those were Safe starts, and the game and launcher version.",
        "l_c": "<b>Hardware, at most once a month.</b> Your Windows version, processor model and thread count, memory and video memory in whole gigabytes, graphics card model, whether DirectX 12 works, desktop resolution and refresh rate, and the launcher language.",
        "l3": "A report never contains your player name, game key, player ID, an install ID, file or folder names on your PC, server addresses or your connection address. Nothing in one report links it to the next, so we cannot tell whether two reports came from the same PC. As with the website, our server looks up the country of the connection, keeps only the two-letter code and forgets the address.",
        "l4": "We keep crash locations and daily counts of starts and crashes per game version for 90 days after we last saw them, and monthly counts per hardware value (for example, how many launchers reported a given graphics card) for 13 months. Memory is grouped into ranges so an unusual amount cannot single anyone out. Because no report carries anything that points to you, there is nothing we could look up to show or delete \"your\" data, and that is by design.",
        "x_h": "Changes to this page",
        "x1": "If what we collect changes, this page changes first, and the devlog says so. Last updated 17 November 2026.",
        "credit": "Country lookup uses IP to Country Lite by <a href=\"https://db-ip.com\">DB-IP</a>, licensed under CC BY 4.0.",
        "n7": "Accounts",
        "n8": "Moderation and support",
        "n9": "Who else",
        "s_e": "<b>A real person answers.</b> Write to <a href=\"mailto:gianni@truecombat.eu\">gianni@truecombat.eu</a> for a copy of your data, a correction or a deletion. We reply within one month.",
        "g_f": "<b>Chat and voice.</b> Text and voice chat travel through the game server to the other players. Our servers do not record voice. Text chat on official servers is kept for 30 days so that reports of abuse can be checked.",
        "a_h": "Player accounts",
        "a1": "Accounts are optional. Nobody needs one to play. If you make one, you sign in with Discord, and we ask Discord for your user ID and name only. The Discord sign-in token is thrown away straight after.",
        "a_a": "<b>What we keep.</b> Your Discord user ID and name, the player name you pick, the PCs you linked (a code made from each PC's game key, plus the label you gave it), any passkeys you add (public keys only), your profile settings, and your previous name for 30 days after a rename.",
        "a_b": "<b>Staying signed in.</b> A sign-in cookie on truecombat.eu keeps you signed in for up to 30 days. The account needs it to work, and it is used for nothing else. Each sign-in is logged with its connection address for 30 days, so we can spot a stolen account.",
        "a_c": "<b>Your profile.</b> Your profile is public unless you set it to hidden, and your Discord name only shows if you switch it on. Accounts are for players aged 13 and over.",
        "a2": "We hold this because you asked for an account (GDPR Article 6(1)(b)), and we keep it until you delete it or stop using it. If you neither play nor sign in for a year, your reserved name is released. After two years without either, we delete the account, with a message on Discord a month before. Your account page has a button that downloads everything we hold about your account, and one that deletes it for good: the account, linked PCs, names, sessions and sign-in log. Match statistics stay on the leaderboards, no longer tied to your account. If the account was banned, the ban keeps a one-way code of your Discord ID so it cannot be dodged with a new account.",
        "m_h": "Moderation, Discord and support",
        "m_a": "<b>Reports and appeals.</b> When a player is reported or banned, moderators keep what they need to decide: the report, the player name and IDs, and evidence such as screenshots or match recordings. Evidence is deleted after a year unless its case is still open. A ban, and any appeal against it with the contact details you choose to give, is kept with the ban record.",
        "m_b": "<b>Discord.</b> Our Discord server and bot see what Discord shares with every server you join. If you link your account, the bot can look up your player name and statistics to post match results and hand out roles. Everything else on Discord falls under <a href=\"https://discord.com/privacy\">Discord's privacy policy</a>.",
        "m_c": "<b>Support on Ko-fi.</b> Donations go through Ko-fi. We store the amount and the name you give, and show that name only if you made your support public. We never store your email address, payment details or message.",
        "p_h": "Who else handles data",
        "p1": "We never sell data or share it for advertising. These companies handle data on our behalf, or run a service you use with us:",
        "p_a": "<b>Hostinger</b>, our server host: game servers, website, statistics and accounts.",
        "p_b": "<b>Cloudflare</b> delivers and protects the website.",
        "p_c": "<b>Zoho</b> handles our email, in its EU data centres.",
        "p_d": "<b>GitHub</b> serves the downloads and the source code, and holds our private nightly server backups. Account data inside those backups is encrypted.",
        "p_e": "<b>Discord</b> for account sign-in and our community. <b>Epic Games</b> for Easy Anti-Cheat on official servers. <b>Ko-fi</b> for donations. <b>YouTube</b> for the trailer, only after you click play.",
        "p2": "Some of these companies are outside the EU. Transfers rely on an EU adequacy decision, such as the EU-US Data Privacy Framework or the decision for the United Kingdom, or on the European Commission's standard contractual clauses.",
    },
    "nl": {
        "title": "Privacy · TrueCombat: Platinum",
        "desc": "Wat de website, de launcher en de servers van TrueCombat: Platinum verzamelen, wat ze nooit verzamelen en hoe je je afmeldt. Geen cookies, geen advertentietrackers, geen analysebedrijven.",
        "og": "Geen cookies, geen advertentietrackers, geen analysebedrijven. Dit is precies wat we tellen.",
        "eyebrow": "Privacy", "h1": "Wat we tellen, en wat we nooit zullen tellen",
        "lede": "We willen weten welke pagina's het lezen waard zijn en waar nieuwe spelers over de game horen. Daarvoor hoeven we niet te weten wie je bent, dus vragen we het ook nooit.",
        "toc": "Op deze pagina", "n1": "Kort samengevat", "n2": "Deze website", "n3": "De game", "n4": "Jouw rechten", "n5": "Wijzigingen",
        "s_h": "Kort samengevat",
        "s_a": "<b>Geen trackingcookies, geen advertentietrackers, geen analysebedrijven.</b> Er wordt niets van Google, Meta of iemand anders op deze site geladen.",
        "s_b": "<b>We tellen bezoeken, geen bezoekers.</b> De website bewaart dagtotalen en niets dat naar een persoon terugleidt.",
        "s_c": "<b>Zegt je browser nee, dan luisteren we.</b> Met Global Privacy Control of Do Not Track aan word je helemaal niet geteld.",
        "s_d": "<b>De launcher deelt crash- en hardwaregegevens alleen als je ja zegt.</b> Hij vraagt het één keer, met twee gelijke knoppen, en je kunt je antwoord altijd wijzigen.",
        "w_h": "Deze website",
        "w1": "Wanneer een pagina opent, stuurt je browser één kort bericht naar onze eigen server: de pagina, de site die naar ons linkte (alleen de naam van de site, nooit het volledige adres), de campagnetag in de link als die er is, de taal van de pagina, en of het scherm de grootte van een telefoon, tablet of desktop heeft. Een klik op een downloadknop stuurt nog één bericht dat er een download is gestart.",
        "w2": "Om je één keer per dag te tellen in plaats van op elke pagina, maakt de server een eenrichtingsvingerafdruk van je verbindingsadres en browser, gemengd met een willekeurig geheim dat alleen die dag bestaat. Met dezelfde vingerafdruk telt een download mee voor de site die je die dag naar ons bracht. Om middernacht UTC worden het geheim en alle vingerafdrukken gewist. Daarna kan niemand de ene dag nog aan de volgende koppelen, ook wij niet.",
        "w3": "De server zoekt het land van je verbindingsadres op in een lijst die op de server zelf staat, bewaart de landcode van twee letters en vergeet het adres. Er wordt geen externe dienst geraadpleegd.",
        "w_keep_h": "Wat we bewaren",
        "w_keep": "Dagtotalen per pagina, verwijzende site, campagne, land, schermgrootte en taal, en hoeveel van die bezoeken tot een download leidden. Voor devlogberichten bewaren we ook hoeveel mensen ze lazen en uitlazen, en hun sterrenbeoordelingen. Deze totalen blijven bewaard zolang de site bestaat.",
        "w_never_h": "Wat we nooit bewaren",
        "w_n1": "Verbindingsadressen (IP), browsergegevens of apparaatinformatie",
        "w_n2": "Cookies, of iets anders dat voor het tellen in je browser wordt opgeslagen",
        "w_n3": "Volledige adressen van de pagina's die je naar ons stuurden",
        "w_n4": "Iets dat een bezoek, beoordeling of download aan een persoon koppelt",
        "w4": "Je browser bewaart een paar kleine notities voor de site zelf, nooit om te tellen: je sterrenbeoordelingen bij devlogberichten, welke devlogberichten je al zag, een kortlevende kopie van de patchnotes en, terwijl je een pc aan je account koppelt, de eenmalige koppelcode. Wis je je browsergegevens, dan verdwijnen ze.",
        "w5": "Live gegevens zoals servers en ranglijsten komen van <code>api.truecombat.eu</code>, en de patchnotes worden naar deze site gekopieerd, zodat je browser GitHub er nooit om vraagt. De site wordt geleverd via Cloudflare, dat hem snel houdt en tegen aanvallen beschermt. De trailer komt pas van YouTube nadat je op afspelen klikt, en downloads komen van GitHub. Zoals elke webserver zien die je verbindingsadres terwijl ze antwoorden.",
        "g_h": "De game en de launcher",
        "g_a": "<b>Online spelen.</b> Gameservers zien je verbindingsadres, zoals bij elke online game. Onze moderatietools bewaren het tot 90 dagen om valsspelen en misbruik aan te pakken, en een ban bewaart het adres dat geband werd.",
        "g_b": "<b>Ranglijsten.</b> Ranked potjes op officiële en geverifieerde servers leggen je spelnaam vast, een speler-ID afgeleid van je gamesleutel en je wedstrijdstatistieken. Daarmee worden de ranglijsten en je openbare profiel gevuld, en die gegevens blijven bewaard zolang de ranglijsten bestaan, want elke rang is erop gebouwd. Elk potje bewaart ook een eenrichtingscode van je verbindingsadres, zodat twee spelers op één verbinding nooit tegen elkaar meetellen; na 90 dagen wordt die code verwijderd. Met een account kun je je profiel altijd verbergen. Zonder account mail je ons en halen we je naam van de openbare pagina's.",
        "g_c": "<b>Anti-cheat.</b> Officiële servers gebruiken Easy Anti-Cheat, dat valt onder het <a href=\"https://www.epicgames.com/site/privacypolicy\">privacybeleid van Epic Games</a>.",
        "g_d": "<b>Crashrapporten en geheugendumps</b> blijven op je pc. Ze komen alleen bij ons als je ze zelf bij een bugmelding voegt. Kies je ervoor om launchergegevens te delen, dan wordt alleen de plek van de crash verstuurd, zoals hieronder beschreven.",
        "g_e": "<b>Bugmeldingen</b> die je vanuit de game verstuurt bevatten wat je schrijft, een screenshot en technische details zoals de map, framerate en grafische kaart, zodat we het probleem kunnen nabootsen. Een melding en haar screenshot worden 90 dagen na het afsluiten gewist.",
        "g_note": "<b>Bekijk het zelf.</b> Instellingen &gt; Privacy &gt; Wat wordt gedeeld in de launcher toont precies het rapport dat je pc als volgende zou versturen, nog voor het je computer verlaat.",
        "c_h": "Jouw keuzes en rechten",
        "c1": "Wil je niet geteld worden op deze website, zet dan Global Privacy Control of Do Not Track aan in je browser. Ook <code>api.truecombat.eu/insights</code> blokkeren werkt, en de site blijft precies hetzelfde werken.",
        "c2": "<b>Jouw rechten.</b> Je kunt een kopie van je gegevens vragen, ze laten verbeteren of wissen, beperken hoe we ze gebruiken, of ze in een overdraagbare vorm krijgen. Je kunt ook bezwaar maken tegen alles wat we op basis van gerechtvaardigd belang doen. Met een account download of wis je alles zelf op de accountpagina. Voor al de rest mail je naar <a href=\"mailto:gianni@truecombat.eu\">gianni@truecombat.eu</a>. We antwoorden binnen een maand, en kunnen vragen om aan te tonen dat de gegevens van jou zijn, bijvoorbeeld door te schrijven vanaf het account in kwestie. Alle telcode staat in de <a href=\"https://github.com/Annoximeme/TrueCombat-Platinum\">openbare repository</a>, dus je hoeft ons nooit op ons woord te geloven.",
        "c3": "<b>Wie verantwoordelijk is.</b> TrueCombat: Platinum wordt gemaakt door Team Terminus. De verwerkingsverantwoordelijke is Gianni Goossens (RaziC*), gevestigd in België en bereikbaar via <a href=\"mailto:gianni@truecombat.eu\">gianni@truecombat.eu</a>. Websitetellingen, het beschermen van de gameservers, moderatie, ranglijsten en back-ups steunen op ons gerechtvaardigd belang bij een eerlijke, veilige game die werkt (AVG artikel 6, lid 1, f), met de waarborgen op deze pagina. Accounts steunen op jouw vraag om er een (artikel 6, lid 1, b). Launchergegevens en bugmeldingen worden alleen met jouw toestemming verstuurd (artikel 6, lid 1, a), die je op elk moment kunt intrekken. Vind je dat we verkeerd met je gegevens omgaan, dan kun je klacht indienen bij een toezichthouder; in België is dat de <a href=\"https://www.gegevensbeschermingsautoriteit.be\">Gegevensbeschermingsautoriteit</a>.",
        "n6": "De launcher",
        "l_h": "Crash- en hardwaregegevens uit de launcher",
        "l1": "Vanaf launcher 2.6.0 vraagt de Spelen-pagina één keer of je anonieme crash- en hardwaregegevens wilt delen. Er wordt niets verstuurd tot je Delen kiest, en helemaal niets als je Nee, bedankt kiest. Dezelfde schakelaar staat bij Instellingen &gt; Privacy, en uitzetten stopt het delen meteen.",
        "l2": "Staat delen aan, dan stuurt de launcher hoogstens één kort rapport per dag naar <code>api.truecombat.eu</code>, en alleen als er iets nieuws te melden is:",
        "l_a": "<b>Crashes.</b> Voor elke nieuwe crash: of de game of de server crashte, de Windows-foutcode, de plek in het programma waar het gebeurde (een bestandsnaam en een positie daarin, zoals <code>renderer_dx12_x64.dll+0x1a2b3</code>), tot vijf stappen die eraan voorafgingen in dezelfde vorm, en hoeveel minuten de game al draaide. De crashrapporten en geheugendumps zelf blijven op je pc.",
        "l_b": "<b>Gamestarts.</b> Hoe vaak de game sinds het vorige rapport is gestart, hoeveel daarvan een Veilige start waren, en de versie van de game en de launcher.",
        "l_c": "<b>Hardware, hoogstens één keer per maand.</b> Je Windows-versie, processormodel en aantal threads, werkgeheugen en videogeheugen in hele gigabytes, het model van je grafische kaart, of DirectX 12 werkt, je bureaubladresolutie en verversingssnelheid, en de taal van de launcher.",
        "l3": "Een rapport bevat nooit je spelnaam, gamesleutel, speler-ID, een installatie-ID, namen van bestanden of mappen op je pc, serveradressen of je verbindingsadres. Niets in een rapport koppelt het aan het volgende, dus we kunnen niet zien of twee rapporten van dezelfde pc komen. Net als bij de website zoekt onze server het land van de verbinding op, bewaart alleen de landcode van twee letters en vergeet het adres.",
        "l4": "We bewaren crashplekken en dagtellingen van starts en crashes per gameversie tot 90 dagen nadat we ze voor het laatst zagen, en maandtellingen per hardwarewaarde (bijvoorbeeld hoeveel launchers een bepaalde grafische kaart meldden) 13 maanden. Geheugen wordt in groepen ingedeeld, zodat een ongewone hoeveelheid niemand herkenbaar maakt. Omdat geen enkel rapport iets bevat dat naar jou wijst, is er niets dat we kunnen opzoeken om \"jouw\" gegevens te tonen of te wissen, en dat is bewust zo.",
        "x_h": "Wijzigingen aan deze pagina",
        "x1": "Als er verandert wat we verzamelen, verandert eerst deze pagina, en de devlog meldt het. Laatst bijgewerkt op 17 november 2026.",
        "credit": "Het opzoeken van landen gebruikt IP to Country Lite van <a href=\"https://db-ip.com\">DB-IP</a>, onder licentie CC BY 4.0.",
        "n7": "Accounts",
        "n8": "Moderatie en steun",
        "n9": "Wie nog",
        "s_e": "<b>Een echt mens antwoordt.</b> Mail naar <a href=\"mailto:gianni@truecombat.eu\">gianni@truecombat.eu</a> voor een kopie van je gegevens, een correctie of een verwijdering. We antwoorden binnen een maand.",
        "g_f": "<b>Chat en spraak.</b> Tekst- en spraakchat gaan via de gameserver naar de andere spelers. Onze servers nemen geen spraak op. Tekstchat op officiële servers wordt 30 dagen bewaard, zodat meldingen van misbruik nagekeken kunnen worden.",
        "a_h": "Spelersaccounts",
        "a1": "Accounts zijn optioneel. Niemand heeft er een nodig om te spelen. Maak je er een, dan meld je je aan met Discord, en vragen we Discord alleen je gebruikers-ID en naam. Het aanmeldtoken van Discord gooien we meteen daarna weg.",
        "a_a": "<b>Wat we bewaren.</b> Je Discord-gebruikers-ID en -naam, de spelnaam die je kiest, de pc's die je koppelde (een code afgeleid van de gamesleutel van elke pc, plus het label dat je eraan gaf), passkeys die je toevoegt (alleen publieke sleutels), je profielinstellingen, en je vorige naam tot 30 dagen na een naamswijziging.",
        "a_b": "<b>Aangemeld blijven.</b> Een aanmeldcookie op truecombat.eu houdt je tot 30 dagen aangemeld. Het account heeft die nodig om te werken, en hij dient voor niets anders. Elke aanmelding wordt 30 dagen gelogd met haar verbindingsadres, zodat we een gestolen account kunnen opmerken.",
        "a_c": "<b>Je profiel.</b> Je profiel is openbaar tenzij je het verbergt, en je Discord-naam verschijnt alleen als je dat aanzet. Accounts zijn voor spelers van 13 jaar en ouder.",
        "a2": "We bewaren dit omdat je om een account vroeg (AVG artikel 6, lid 1, b), en we bewaren het tot je het verwijdert of niet meer gebruikt. Speel je een jaar niet en meld je je niet aan, dan komt je gereserveerde naam weer vrij. Na twee jaar zonder beide wissen we het account, met een bericht op Discord een maand vooraf. Je accountpagina heeft een knop die alles downloadt wat we over je account bewaren, en een knop die het definitief wist: het account, gekoppelde pc's, namen, sessies en het aanmeldlogboek. Wedstrijdstatistieken blijven op de ranglijsten staan, los van je account. Werd het account geband, dan bewaart de ban een eenrichtingscode van je Discord-ID, zodat hij niet te omzeilen is met een nieuw account.",
        "m_h": "Moderatie, Discord en steun",
        "m_a": "<b>Meldingen en bezwaren.</b> Wordt een speler gemeld of geband, dan bewaren moderators wat ze nodig hebben om te beslissen: de melding, de spelnaam en ID's, en bewijs zoals screenshots of wedstrijdopnames. Bewijs wordt na een jaar gewist, tenzij de zaak nog openstaat. Een ban, en elk bezwaar ertegen met de contactgegevens die je zelf opgeeft, blijft bij het banrecord bewaard.",
        "m_b": "<b>Discord.</b> Onze Discord-server en bot zien wat Discord met elke server deelt waar je lid van wordt. Koppel je je account, dan kan de bot je spelnaam en statistieken opzoeken om wedstrijduitslagen te posten en rollen toe te kennen. Al de rest op Discord valt onder het <a href=\"https://discord.com/privacy\">privacybeleid van Discord</a>.",
        "m_c": "<b>Steun via Ko-fi.</b> Donaties lopen via Ko-fi. We bewaren het bedrag en de naam die je opgeeft, en tonen die naam alleen als je je steun openbaar maakte. Je e-mailadres, betaalgegevens of bericht bewaren we nooit.",
        "p_h": "Wie nog met gegevens werkt",
        "p1": "We verkopen nooit gegevens en delen ze nooit voor reclame. Deze bedrijven verwerken gegevens in onze opdracht, of draaien een dienst die je met ons gebruikt:",
        "p_a": "<b>Hostinger</b>, onze serverhost: gameservers, website, statistieken en accounts.",
        "p_b": "<b>Cloudflare</b> levert en beschermt de website.",
        "p_c": "<b>Zoho</b> verzorgt onze e-mail, in zijn Europese datacenters.",
        "p_d": "<b>GitHub</b> levert de downloads en de broncode, en bewaart onze privé nachtelijke serverback-ups. Accountgegevens in die back-ups zijn versleuteld.",
        "p_e": "<b>Discord</b> voor het aanmelden en onze community. <b>Epic Games</b> voor Easy Anti-Cheat op officiële servers. <b>Ko-fi</b> voor donaties. <b>YouTube</b> voor de trailer, pas nadat je op afspelen klikt.",
        "p2": "Sommige van deze bedrijven zitten buiten de EU. Doorgifte steunt op een adequaatheidsbesluit van de EU, zoals het EU-VS-gegevensprivacykader of het besluit voor het Verenigd Koninkrijk, of op de modelcontractbepalingen van de Europese Commissie.",
    },
}


def fill(template, table, values):
    out = template
    for k, v in values.items():
        out = out.replace("{{%s}}" % k, v)
    for k, v in table.items():
        if isinstance(v, str):
            out = out.replace("[[%s]]" % k, v)
    return out


def faq_body(lang, values):
    T = FAQ[lang]
    toc = "".join('<a href="#%s">%s</a>' % (gid, title) for gid, title, _ in T["groups"])
    groups = ""
    for n, (gid, title, items) in enumerate(T["groups"], 1):
        qa = "\n".join('          <div id="%s"><h3>%s</h3><p>%s</p></div>' % (qid, q, a) for qid, q, a in items)
        groups += f"""
      <section id="{gid}">
        <span class="eyebrow">{n:02d}</span>
        <h2>{title}</h2>
        <div class="faq">
{qa}
        </div>
      </section>
"""
    return fill(f"""<section class="page-head">
  <div class="head-art" style="--art: url({{{{up}}}}img/hero-stadtrand-canal.webp); --art-s: url({{{{up}}}}img/hero-stadtrand-canal-640.webp)" aria-hidden="true"></div>
  <div class="wrap">
    <span class="eyebrow">{T['eyebrow']}</span>
    <h1>{T['h1']}</h1>
    <p class="lede">{T['lede']}</p>
  </div>
</section>

<section class="band">
  <div class="wrap doc">
    <nav class="doc-toc" aria-label="{T['toc']}">
      {toc}
    </nav>
    <div class="doc-body">{groups}
      <p class="callout"><b>{T['more_h']}</b> {T['more']}</p>
    </div>
  </div>
</section>
""", {}, values)


def elite_body(lang, values):
    T = ELITE_T[lang]
    rows = "\n".join('              <tr><th scope="row">%s</th><td data-label="%s">%s</td><td data-label="TrueCombat: Platinum">%s</td></tr>' % (r[0], T["c_orig"], r[1], r[2]) for r in T["rows"])
    return fill(ELITE, T, values).replace("[[rows]]", rows)


def body(page, lang, values):
    if page == "download":
        return fill(DOWNLOAD, DOWNLOAD_T[lang], values)
    if page == "faq":
        return faq_body(lang, values)
    if page == "privacy":
        return fill(PRIVACY, PRIVACY_T[lang], values)
    return elite_body(lang, values)


def meta(page, lang):
    T = {"download": DOWNLOAD_T, "faq": FAQ, "truecombat-elite": ELITE_T, "privacy": PRIVACY_T}[page][lang]
    return T["title"], T["desc"], T["og"]


def faq_items(lang):
    """(question, answer html) for every FAQ entry: used for structured data and the site search."""
    return [(qid, q, a) for _, _, items in FAQ[lang]["groups"] for qid, q, a in items]
