/* test_bot_listen.c: checks for tcp_bot_listen.h.   cc -std=c99 -Wall -Wextra -O1 test_bot_listen.c -o test_bot_listen
 * Run: ./test_bot_listen [phrases.txt]   (with the bank, also checks every reply key exists and can produce a line) */
#include <stdio.h>
#include <stdlib.h>
#include "tcp_bot_chat.h"
#include "tcp_bot_listen.h"

static const char *const bots[] = { "Viper", "Warden", "Ghost", "Sparrow", "Falcon", "^1Rook", "Storm" };
static const char *const areas[] = { "Courtyard", "Tunnel", "Site A", "Site B", "Back Alley", "Alley", "Market", "Long Hall", "Tunnel 2" };
#define NB 7
#define NA 9
static int fails, checks;

typedef struct { const char *text; int intent, addressed, target, area; } tcase_t;
#define N BOTLISTEN_NONE
#define G BOTLISTEN_GROUP
#define B BOTLISTEN_NAMED
static const tcase_t cases[] = {
    /* named orders */
    { "viper hold", BL_HOLD, B, 0, -1 }, { "Viper, hold here!", BL_HOLD, B, 0, -1 }, { "hold site a viper", BL_HOLD, B, 0, 2 },
    { "ghost follow me", BL_FOLLOW, B, 2, -1 }, { "GHOST ON ME", BL_FOLLOW, B, 2, -1 }, { "^2ghost^7 with me", BL_FOLLOW, B, 2, -1 },
    { "rook watch tunnel", BL_WATCH, B, 5, 1 }, { "sparrow smoke market pls", BL_SMOKE, B, 3, 6 }, { "sparrow flash me", BL_FLASH, B, 3, -1 },
    { "falcon go to long hall", BL_GOTO, B, 4, 7 }, { "falcon long hall", BL_GOTO, B, 4, 7 }, { "warden back alley", BL_GOTO, B, 1, 4 },
    { "warden alley", BL_GOTO, B, 1, 5 }, { "storm tunnel 2", BL_GOTO, B, 6, 8 }, { "storm go tunnel", BL_GOTO, B, 6, 1 },
    { "viper go first", BL_LEAD, B, 0, -1 }, { "viper drop the bomb", BL_DROP_BOMB, B, 0, -1 }, { "ghost take the bomb", BL_TAKE_BOMB, B, 2, -1 },
    { "ghost flank", BL_FLANK, B, 2, -1 }, { "warden defuse!!", BL_DEFUSE, B, 1, -1 }, { "viper plant b", BL_PLANT, B, 0, 3 },
    { "viper cover me", BL_COVER, B, 0, -1 }, { "falcon nade courtyard", BL_FRAG, B, 4, 0 }, { "viper wait", BL_WAIT, B, 0, -1 },
    { "viper nvm", BL_CANCEL, B, 0, -1 }, { "viper", BL_NAME_ONLY, B, 0, -1 }, { "Ghost?", BL_NAME_ONLY, B, 2, -1 }, { "viper!!!", BL_NAME_ONLY, B, 0, -1 },
    /* group orders */
    { "bots push a", BL_PUSH, G, -1, 2 }, { "team rush b", BL_PUSH, G, -1, 3 }, { "guys regroup", BL_REGROUP, G, -1, -1 },
    { "everyone to site b", BL_STACK, G, -1, 3 }, { "all bots follow me", BL_FOLLOW, G, -1, -1 }, { "bots spread out", BL_SPREAD, G, -1, -1 },
    { "bots dont stack", BL_SPREAD, G, -1, -1 }, { "team fall back", BL_FALLBACK, G, -1, -1 }, { "bots walk", BL_QUIET, G, -1, -1 },
    { "team all push a", BL_STACK, G, -1, 2 }, { "bots help me", BL_HELP, G, -1, -1 }, { "bots market", BL_GOTO, G, -1, 6 },
    /* unaddressed: still parsed, caller decides */
    { "push a", BL_PUSH, N, -1, 2 }, { "follow me", BL_FOLLOW, N, -1, -1 }, { "go go go", BL_PUSH, N, -1, -1 }, { "go b", BL_GOTO, N, -1, 3 },
    { "go", BL_PUSH, N, -1, -1 }, { "smoke tunnel", BL_SMOKE, N, -1, 1 }, { "need backup", BL_HELP, N, -1, -1 }, { "rotate b", BL_GOTO, N, -1, 3 },
    { "wait", BL_WAIT, N, -1, -1 }, { "hold", BL_HOLD, N, -1, -1 },
    /* negation */
    { "viper dont push", BL_WAIT, B, 0, -1 }, { "bots don't push yet", BL_WAIT, G, -1, -1 }, { "viper stop following", BL_CANCEL, B, 0, -1 },
    { "ghost dont follow me", BL_CANCEL, B, 2, -1 }, { "bots do not go a", BL_WAIT, G, -1, 2 }, { "viper dont wait", BL_PUSH, B, 0, -1 },
    { "bots no smoke", BL_CANCEL, G, -1, -1 },
    /* questions */
    { "are you a bot?", BL_ASK_BOT, G, -1, -1 }, { "viper are you a bot", BL_ASK_BOT, B, 0, -1 }, { "r u a bot", BL_ASK_BOT, G, -1, -1 },
    { "are you bots?", BL_ASK_BOT, G, -1, -1 }, { "ben je een bot?", BL_ASK_BOT, G, -1, -1 },
    { "ghost where are you", BL_ASK_STATUS, B, 2, -1 }, { "falcon status", BL_ASK_STATUS, B, 4, -1 }, { "how many left?", BL_ASK_COUNT, N, -1, -1 },
    { "how many b", BL_ASK_COUNT, N, -1, 3 }, { "who has the bomb", BL_ASK_BOMB, N, -1, -1 }, { "where's the bomb?", BL_ASK_BOMB, N, -1, -1 },
    { "viper where is he", BL_ASK_OTHER, B, 0, -1 }, { "bots what now?", BL_ASK_OTHER, G, -1, -1 }, { "any info", BL_ASK_OTHER, N, -1, -1 },
    /* social */
    { "ty", BL_THANKS, N, -1, -1 }, { "thanks viper", BL_THANKS, B, 0, -1 }, { "merci!", BL_THANKS, N, -1, -1 }, { "sry", BL_SORRY, N, -1, -1 },
    { "my bad", BL_SORRY, N, -1, -1 }, { "hi all", BL_GREETING, N, -1, -1 }, { "hey guys", BL_GREETING, G, -1, -1 }, { "hallo", BL_GREETING, N, -1, -1 },
    { "gg", BL_GG, N, -1, -1 }, { "GG WP", BL_GG, N, -1, -1 }, { "glhf", BL_GLHF, N, -1, -1 }, { "gl hf all", BL_GLHF, N, -1, -1 },
    { "bye", BL_BYE, N, -1, -1 }, { "gtg cya", BL_BYE, N, -1, -1 }, { "nice shot falcon", BL_COMPLIMENT, B, 4, -1 }, { "ns", BL_COMPLIMENT, N, -1, -1 },
    { "good bot", BL_COMPLIMENT, G, -1, -1 }, { "stupid bots", BL_INSULT, G, -1, -1 }, { "viper you suck", BL_INSULT, B, 0, -1 },
    { "noob", BL_INSULT, N, -1, -1 }, { "wtf viper", BL_BLAME, B, 0, -1 }, { "lol", BL_LAUGH, N, -1, -1 }, { "hahaha", BL_LAUGH, N, -1, -1 },
    { "nt", BL_NICE_TRY, N, -1, -1 }, { "unlucky", BL_NICE_TRY, N, -1, -1 }, { "desol\xC3\xA9", BL_SORRY, N, -1, -1 }, { "bien jou\xE9", BL_COMPLIMENT, N, -1, -1 },
    /* must not trigger */
    { "", BL_NONE, N, -1, -1 }, { "?", BL_NONE, N, -1, -1 }, { "anyone want to play 5v5 later", BL_NONE, N, -1, -1 },
    { "this map is huge", BL_NONE, N, -1, -1 }, { "I was in the tunnel when he shot me", BL_NONE, N, -1, 1 },
    { "brb phone", BL_NONE, N, -1, -1 }, { "my ping is terrible today", BL_NONE, N, -1, -1 }, { "i will be back in five minutes ok", BL_NONE, N, -1, -1 },
    { "can someone take a look at the server", BL_NONE, N, -1, -1 }, { "holding", BL_NONE, N, -1, -1 }, { "pushed", BL_NONE, N, -1, -1 },
    { "vipers are cool", BL_NONE, N, -1, -1 }, { "what a round that was", BL_NONE, N, -1, -1 },
};

static void runCase(const tcase_t *c)
{
    botlisten_t r; int ok = botListenParse(c->text, bots, NB, areas, NA, &r);
    checks++;
    if (r.intent != c->intent || r.addressed != c->addressed || r.target != c->target || r.area != c->area || ok != (c->intent != BL_NONE)) {
        fails++;
        printf("FAIL \"%s\": got %s/%d/%d/%d, want %s/%d/%d/%d\n", c->text, botListenNames[r.intent], r.addressed, r.target, r.area,
               botListenNames[c->intent], c->addressed, c->target, c->area);
    }
}

int main(int argc, char **argv)
{
    (void)botChatLastCall; (void)botChatFrame; (void)botChatCancel; (void)botChatSetVoice; (void)botChatSay;
    for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) runCase(&cases[i]);
    /* every intent has a name and (except none) a reply key for both can / can't */
    for (int i = 0; i < BL_COUNT; i++) { checks++; if (!botListenNames[i]) { fails++; printf("FAIL no name %d\n", i); } }
    for (int i = 1; i < BL_COUNT; i++) for (int can = 0; can < 2; can++) { checks++; if (!botListenReplyKey(i, can)) { fails++; printf("FAIL no reply key %s\n", botListenNames[i]); } }
    /* robustness: junk, long lines, NULL lists, random bytes */
    { botlisten_t r; char big[600]; unsigned s = 12345;
      checks++; if (botListenParse(NULL, bots, NB, areas, NA, &r)) fails++;
      checks++; botListenParse("viper hold a", NULL, 0, NULL, 0, &r); if (r.intent != BL_HOLD || r.target != -1) { fails++; printf("FAIL null lists\n"); }
      for (int t = 0; t < 20000; t++) {
          int l = (int)(s % 599); for (int i = 0; i < l; i++) { s = s * 1103515245u + 12345u; big[i] = (char)((s >> 16) % 255 + 1); } big[l] = 0;
          botListenParse(big, bots, NB, areas, NA, &r); checks++;
          if (r.intent < 0 || r.intent >= BL_COUNT || r.target >= NB || r.area >= NA) { fails++; printf("FAIL fuzz range\n"); break; }
      }
      /* fuzz with real words glued together */
      static const char *const w[] = { "viper", "bots", "push", "dont", "a", "b", "tunnel", "hold", "go", "to", "site", "smoke", "?", "!", "the", "me", "all", "stop", "ghost", "^1", "'", "back", "alley" };
      for (int t = 0; t < 50000; t++) {
          big[0] = 0; int n = 1 + (int)(s % 9);
          for (int i = 0; i < n; i++) { s = s * 1103515245u + 12345u; strcat(big, w[(s >> 16) % (sizeof(w) / sizeof(w[0]))]); strcat(big, " "); }
          botListenParse(big, bots, NB, areas, NA, &r); checks++;
          if (r.intent < 0 || r.intent >= BL_COUNT || r.target >= NB || r.area >= NA || (r.addressed == BOTLISTEN_NAMED) != (r.target >= 0)) { fails++; printf("FAIL word fuzz \"%s\"\n", big); break; }
      }
    }
    if (argc > 1) {
        FILE *f = fopen(argv[1], "rb"); if (!f) { printf("cannot open %s\n", argv[1]); return 2; }
        static char buf[2 * 1024 * 1024]; int len = (int)fread(buf, 1, sizeof(buf) - 1, f); fclose(f);
        int n = botChatLoad(buf, len); checks++; if (n <= 0) { fails++; printf("FAIL bank load %d\n", n); }
        botchat_ctx_t ctx = { "Tunnel", 2, "RaziC", "Player" }; char out[128];
        for (int i = 1; i < BL_COUNT; i++) for (int can = 0; can < 2; can++) {
            const char *k = botListenReplyKey(i, can); int sit = botChatSituation(k); checks++;
            if (sit < 0) { fails++; printf("FAIL reply key %s not in bank\n", k); continue; }
            for (int p = 0; p < 5; p++) { checks++; if (!botChatPick(sit, p, 0, &ctx, out, sizeof(out), 0)) { fails++; printf("FAIL no line for %s pers %d\n", k, p); } }
        }
    }
    printf("%d checks, %d failed\n", checks, fails);
    return fails ? 1 : 0;
}
