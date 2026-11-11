# Bot chat runtime

`tcp_bot_chat.h` loads the phrase bank and decides what a bot says and when. Self-contained C99, no engine
includes, no allocation after load (about 0.6 MB of static memory). It follows the pattern of the other
`tcp_bot_*.h` headers: include it from `tcp_bots.h` after the personality code.

| File | What it is |
|---|---|
| `tcp_bot_chat.h` | Loader, line picker, pacing queue |
| `test_bot_chat.c` | 250,000 checks: every line of every situation fills cleanly, pacing, cooldowns, bad input |
| `tcp_bot_listen.h` | Understands what a human types to the bots: orders, questions, small talk |
| `test_bot_listen.c` | 70,000 checks: 110 hand-written chat lines, random input, every reply exists in the bank |
| `sim_chat.c` | Plays made-up rounds (bomb attack, bomb defence, flag, deathmatch) and prints the chat, using the real picker and parser |
| `sample-rounds.txt` | Eight simulated rounds to read, two of each mode |

## Hooking it up

```c
#include "tcp_bot_chat.h"

/* map load: read phrases.txt with the engine's file calls, then */
botChatLoad(buf, len);                       /* returns line count, negative on a bad file */
botChat.mode = SystemCall(G_CVAR_VARIABLE_INTEGER_VALUE, "bot_chat");   /* 0 off, 1 team, 2 team and all */
static int sitContactOne; sitContactOne = botChatSituation("contact_one");   /* resolve keys once */

/* when a bot joins: voice from the roster */
botChatSetVoice(slot, roster->chatty, roster->lower);

/* when something happens */
botchat_ctx_t c = { areaName, enemyCount, teammateName, enemyName };   /* leave unknown fields 0 */
botChatSay(levelTime, slot, team, personality, sitContactOne, &c, 0);

/* every server frame */
botChatFrame(levelTime, botChatEmit);

/* round start */
botChatRoundReset();
```

`botChatEmit(slot, team, channel, sit, text)` sends the line. The existing `botTeamSay` in `tcp_bot_obj.h`
already builds the right `tchat` command; reuse its body for `BOTCHAT_TEAM` and the `chat` equivalent for
`BOTCHAT_ALL`. Its 4 second team limit should go, because pacing lives here now. The seven fixed lines in
`tcp_bot_obj.h` ("I have the bomb. Moving to site A.") map to `bomb_site_choice`, `bomb_defusing`,
`flag_taken`, `flag_lost`, `enemy_bomb_planted` and `bomb_planted`.

Text is safe to put in a server command: names and areas are stripped of colour codes, quotes, semicolons,
percent signs and control characters before they are filled in.

## Flags

- `BOTCHAT_FORCE`: replies to human orders and pings. Skips chattiness and the per-bot cap.
- `BOTCHAT_NODELAY`: no typing delay, for grenade warnings and what a dying bot saw.
- `BOTCHAT_DEAD`: the speaker is dead. The caller decides which situations a dead bot may use.

## What it does for you

- Skips lines whose placeholders can't be filled, lines over 64 characters, and lines that would repeat a
  landmark word of the area name.
- Never repeats one of the last 8 lines for the same situation on the same team.
- Typing delay of 0.4 to 1.2 s plus 12 ms per character. One line per team every 1.5 s. Three lines per bot
  per 10 s. Per-situation cooldowns from the bank. A line that waits more than 2.5 s past its time is dropped.
- Chattiness per bot. Contact calls, objective calls and death info get a floor of 75%, so quiet bots still
  report what matters. Everything else is small talk and follows the bot's own chattiness.
- One line in ten borrows another personality's voice.
- `botChatLastCall()` remembers each bot's last call for the simple follow-ups.
- `botChat.why[]` counts why requests were held back (typing, quiet, cap, cooldown, stale, no line).

Two rules the caller must keep: request a reply to another line (`fu_ack_teammate_call`, `fu_thanks_teammate`)
from the emit callback of the line it answers, and call `botChatCancel(slot, sit)` when a queued call goes
stale (the enemy died, the area was cleared).

## Build and run

```
cc -std=c99 -Wall -Wextra -O1 -fsanitize=address,undefined test_bot_chat.c -o test_bot_chat && ./test_bot_chat ../phrases/phrases.txt
cc -std=c99 -Wall -Wextra -O1 -fsanitize=address,undefined test_bot_listen.c -o test_bot_listen && ./test_bot_listen ../phrases/phrases.txt
cc -std=c99 -O1 sim_chat.c -o sim_chat && ./sim_chat ../phrases/phrases.txt ../roster/roster.txt 5 8 --events --game mix
```

`--game attack|defend|ctf|tdm|mix` picks the mode (default attack; mix cycles through all four).

`sim_chat` takes a seed and a round count. `--events` shows what happened, `--why` also shows why a bot stayed
silent, `--mode 1` turns all-chat off. Built and tested with gcc and clang on Linux; not yet compiled with the
project's Windows toolchain.

## Listening: orders typed by players

`tcp_bot_listen.h` turns a chat line into an intent, who it is for and which area it names. Keyword matching
on the server, no language model. Hook it into the server's chat handler for team chat from humans:

```c
#include "tcp_bot_listen.h"

botlisten_t r;
if (botListenParse(text, botNamesOnTeam, numBots, areaNames, numAreas, &r)) {
    /* r.intent     BL_FOLLOW, BL_HOLD, BL_PUSH, BL_GOTO, BL_SMOKE ... BL_ASK_COUNT ... BL_THANKS ... (40 intents)
       r.addressed  BOTLISTEN_NAMED ("viper hold"), BOTLISTEN_GROUP ("bots push a"), BOTLISTEN_NONE ("push a")
       r.target     index of the named bot, or -1
       r.area       index of the area named, or -1 ("a" and "b" match "Site A" and "Site B" as the last word) */
    int can = /* your check: alive, close enough, has the grenade, not carrying the bomb ... */;
    botChatSay(now, slot, team, pers, botChatSituation(botListenReplyKey(r.intent, can)), &ctx, BOTCHAT_FORCE);
}
```

What it handles, all covered by tests:

- 23 orders (follow, hold, push, go to an area, regroup, cover, watch, smoke, flash, frag, drop or take the bomb,
  plant, defuse, spread, quiet, flank, wait, fall back, lead, stack, cancel, help), 5 questions (where are you,
  how many, who has the bomb, are you a bot, anything else) and 11 kinds of small talk (thanks, sorry, hi, bye,
  gg, glhf, praise, insults, blame, laughing, nice try).
- About 330 phrasings, with a little Dutch, French and German ("volg mij", "attends", "hilfe").
- Negation: "dont push" becomes wait, "dont wait" becomes push, "stop following" cancels.
- Colour codes, capitals, punctuation and accents are ignored. Bot names with colour codes match.
- It does not react to ordinary talk. With nobody addressed, an order without an area or a social line only
  counts when the message is four words or shorter ("I will be back in five minutes" is not a fall-back order).

The parser never decides whether a bot obeys. Suggested policy: a named bot always answers; for a group order
the two nearest free bots answer and the rest just do it; an order with nobody addressed is obeyed only from
the squad leader, or when the sender is the only human on the team. Questions and small talk get one answer
from one bot. `BL_ASK_BOT` must always be answered (honesty rule), and `BL_INSULT` only with `reply_insult`.

## Tuning

Simulated five-bot teams say about 19 lines per round, one every 5 seconds. If that is too much in a real
match, the levers are the team gap (1500 ms in `botChatFrame`), the 75% floor in `botChatSay`, and the
`chatty` column in the roster.
