/* Launcher version, kept separate from the game version.
   Bump it with every launcher change: MAJOR for a new launcher generation,
   MINOR for new features, PATCH for fixes. The three numbers and the text
   must agree (make_update_feed.py checks this).
   make_update_feed.py writes launcher_version= into the signed update.txt, and
   a launcher that sees a newer one there replaces itself without touching the
   game files. Preprocessor lines only: platinum_launcher.rc includes this file. */
#define PLATINUM_LAUNCHER_MAJOR 2
#define PLATINUM_LAUNCHER_MINOR 6
#define PLATINUM_LAUNCHER_PATCH 2
#define PLATINUM_LAUNCHER_VERSION_TEXT "2.6.2"
#define PLATINUM_LAUNCHER_VERSION L"" PLATINUM_LAUNCHER_VERSION_TEXT
/* Embedded as UTF-16 so tooling and the self-updater can confirm which launcher an EXE is. */
#define PLATINUM_LAUNCHER_MARKER L"TrueCombatPlatinumLauncher/" PLATINUM_LAUNCHER_VERSION_TEXT
