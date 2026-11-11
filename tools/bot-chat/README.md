# Bot chat kit

Everything the bots need to talk in team chat and to understand typed orders. Not wired into the game yet.

| Folder | Contents |
|---|---|
| `phrases/` | Phrase bank: `phrases.txt` (loaded by the game), `phrases.json`, the situation index and the source lists with their build script |
| `chat/` | `tcp_bot_chat.h` (loader, line picker, pacing), `tcp_bot_listen.h` (order parser), tests and the chat simulator |
| `roster/` | Personality and chat traits for the 32 bot names |
| `voice/` | Map from chat situations to radio voice lines, and the check against the game's voice scripts |

Each folder has its own README.
