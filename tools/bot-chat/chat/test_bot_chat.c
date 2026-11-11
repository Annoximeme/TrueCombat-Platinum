/* Tests for tcp_bot_chat.h. Build: cc -std=c99 -Wall -Wextra -O1 -fsanitize=address,undefined test_bot_chat.c -o test_bot_chat
 * Run: ./test_bot_chat ../phrases.txt */
#include "tcp_bot_chat.h"
static int fails, checks;
#define CHECK(c, ...) do { checks++; if (!(c)) { fails++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)
static char last[BOTCHAT_OUT]; static int emitted, lastSlot, lastChan;
static void emit(int slot, int team, int channel, int sit, const char *text) { (void)team; (void)sit; emitted++; lastSlot = slot; lastChan = channel; snprintf(last, sizeof(last), "%s", text); }
int main(int argc, char **argv)
{
    FILE *f = fopen(argc > 1 ? argv[1] : "phrases.txt", "rb"); if (!f) { printf("no bank\n"); return 2; }
    fseek(f, 0, SEEK_END); long len = ftell(f); fseek(f, 0, SEEK_SET);
    char *text = malloc((size_t)len); if (fread(text, 1, (size_t)len, f) != (size_t)len) return 2; fclose(f);
    int n = botChatLoad(text, (int)len); free(text);
    printf("loaded %d lines, %d situations, arena %d bytes\n", n, botChat.numSits, botChat.arenaUsed);
    CHECK(n > 8000, "line count %d", n);
    CHECK(botChat.numSits > 300, "situations %d", botChat.numSits);
    CHECK(botChatSituation("nope") == -1, "unknown key");
    int one = botChatSituation("contact_one"), many = botChatSituation("contact_many"), gg = botChatSituation("match_won"),
        ord = botChatSituation("order_hold"), lost = botChatSituation("contact_lost"), up = botChatSituation("enemy_above");
    CHECK(one >= 0 && many >= 0 && gg >= 0 && ord >= 0 && lost >= 0 && up >= 0, "keys resolve");
    CHECK(botChat.sits[gg].channel == BOTCHAT_ALL && botChat.sits[one].channel == BOTCHAT_TEAM, "channels");
    CHECK(botChat.sits[one].cooldownMs == 6000, "cooldown %d", botChat.sits[one].cooldownMs);
    /* every situation has every personality, every line fills with a full context, no leftovers */
    botchat_ctx_t full = { "^1The COURTYARD", 3, "[TT] RaziC*", "^4Ravo^7C" }; char out[BOTCHAT_OUT];
    for (int s = 0; s < botChat.numSits; s++) for (int p = 0; p < BOTCHAT_PERS; p++) {
        CHECK(botChat.sits[s].count[p] >= 4, "%s/%s has %d lines", botChat.sits[s].key, botChatPersNames[p], botChat.sits[s].count[p]);
        for (int k = 0; k < 40; k++) {
            int ok = botChatPick(s, p, 1, &full, out, sizeof(out), 25);
            CHECK(ok, "%s/%s picks", botChat.sits[s].key, botChatPersNames[p]);
            CHECK(!strchr(out, '{') && !strchr(out, '^') && !strchr(out, '"') && !strchr(out, '%'), "clean text: %s", out);
            CHECK(strlen(out) <= BOTCHAT_MAX_TEXT, "length: %s", out);
            CHECK(!strstr(out, "The COURTYARD") && !strstr(out, "COURTYARD"), "area cleaned: %s", out);
        }
    }
    /* lines needing a missing placeholder are never used */
    botchat_ctx_t noarea = { 0, 0, 0, 0 };
    for (int k = 0; k < 300; k++) if (botChatPick(lost, k % BOTCHAT_PERS, 1, &noarea, out, sizeof(out), 0)) CHECK(!strstr(out, "Courtyard"), "no area leak: %s", out);
    int kc = botChatSituation("kill_confirm");
    for (int k = 0; k < 300; k++) { CHECK(botChatPick(kc, k % BOTCHAT_PERS, 1, &noarea, out, sizeof(out), 0), "kill_confirm without ctx"); CHECK(!strchr(out, '{'), "unfilled: %s", out); }
    CHECK(!botChatPick(one, 0, 1, &noarea, out, sizeof(out), 0), "contact_one needs an area");
    /* area word clash */
    botchat_ctx_t roof = { "Roof", 0, 0, 0 };
    for (int k = 0; k < 400; k++) if (botChatPick(up, k % BOTCHAT_PERS, 1, &roof, out, sizeof(out), 0)) {
        char low[BOTCHAT_OUT]; int i = 0; for (; out[i]; i++) low[i] = (char)botChatLower((unsigned char)out[i]); low[i] = 0;
        char *a = strstr(low, "roof"); CHECK(!(a && strstr(a + 4, "roof")), "roof twice: %s", out);
    }
    /* no repeat inside the window */
    short seen[BOTCHAT_WINDOW]; memset(seen, 0xff, sizeof(seen)); botchat_ctx_t c1 = { "Shed", 0, 0, 0 };
    char prev[BOTCHAT_WINDOW][BOTCHAT_OUT]; memset(prev, 0, sizeof(prev));
    botChat.seed = 99; int rep = 0;
    for (int k = 0; k < 500; k++) {
        botChatPick(one, BOTCHAT_ANCHOR, 2, &c1, out, sizeof(out), 0);
        for (int r = 0; r < BOTCHAT_WINDOW - 1; r++) if (!strcmp(prev[r], out)) rep++;
        memmove(prev[1], prev[0], sizeof(prev) - sizeof(prev[0])); snprintf(prev[0], sizeof(prev[0]), "%s", out);
    }
    CHECK(rep == 0, "repeats inside window: %d", rep);
    /* pacing: typing delay, team gap, bot cap, cooldown, force, mode */
    botChatRoundReset(); emitted = 0; int now = 100000;
    for (int s = 0; s < 8; s++) botChatSetVoice(s, 100, 25);
    CHECK(botChatSay(now, 1, 1, BOTCHAT_ENTRY, one, &c1, 0) == 1, "queued");
    botChatFrame(now + 50, emit); CHECK(emitted == 0, "typing delay");
    botChatFrame(now + 2500, emit); CHECK(emitted == 1 && lastSlot == 1, "emitted after delay");
    CHECK(botChatSay(now + 2600, 1, 1, BOTCHAT_ENTRY, one, &c1, 0) == 0, "situation cooldown");
    CHECK(botChatSay(now + 2600, 1, 1, BOTCHAT_ENTRY, ord, &c1, BOTCHAT_FORCE) == 1, "orders always answered");
    CHECK(botChatSay(now + 2600, 2, 1, BOTCHAT_SUPPORT, many, &full, 0) == 1, "second bot queued");
    botChatFrame(now + 2700, emit); CHECK(emitted == 1, "team gap holds lines back");
    botChatFrame(now + 4100, emit); CHECK(emitted == 2, "one line after the gap, got %d", emitted);
    botChatFrame(now + 5700, emit); CHECK(emitted == 3, "next line after another gap, got %d", emitted);
    now += 20000; int q = 0;
    for (int k = 0; k < 6; k++) { q += botChatSay(now, 3, 1, BOTCHAT_SUPPORT, kc, &noarea, 0); now += 1600; botChatFrame(now, emit); }
    CHECK(q <= 4, "bot cap: %d lines in 10 s", q);
    now += 20000; emitted = 0;
    botChatSay(now, 4, 1, BOTCHAT_ANCHOR, one, &c1, 0); botChatCancel(4, one); botChatFrame(now + 3000, emit); CHECK(emitted == 0, "cancel");
    botChat.mode = 1; CHECK(botChatSay(now, 5, 1, BOTCHAT_ENTRY, gg, &noarea, BOTCHAT_FORCE) == 0, "all-chat off in mode 1");
    botChat.mode = 0; CHECK(botChatSay(now, 5, 1, BOTCHAT_ENTRY, kc, &noarea, BOTCHAT_FORCE) == 0, "mode 0 silent");
    botChat.mode = 2; CHECK(botChatSay(now, 5, 1, BOTCHAT_ENTRY, gg, &noarea, BOTCHAT_FORCE) == 1, "mode 2 all chat");
    botChatFrame(now + 3000, emit); CHECK(lastChan == BOTCHAT_ALL, "channel passed to emit");
    /* stale lines are dropped, not sent late */
    now += 20000; emitted = 0; botChat.teamNext[1] = now + 60000;
    botChatSay(now, 6, 1, BOTCHAT_ANCHOR, kc, &noarea, BOTCHAT_FORCE); botChatFrame(now + 9000, emit); CHECK(emitted == 0 && botChat.qn == 0, "stale drop");
    /* chattiness 0 never speaks, last call memory, bad input */
    botChatSetVoice(7, 0, 25); int spoke = 0; for (int k = 0; k < 50; k++) spoke += botChatSay(now + k * 20000, 7, 2, BOTCHAT_LURKER, kc, &noarea, 0);
    CHECK(spoke == 0, "chattiness 0");
    botChatRoundReset(); botChatSay(now, 1, 1, BOTCHAT_ENTRY, one, &c1, BOTCHAT_FORCE); const char *la = 0;
    CHECK(botChatLastCall(1, now + 5000, 20000, &la) == one && la && !strcmp(la, "Shed"), "last call memory");
    CHECK(botChatLastCall(1, now + 50000, 20000, &la) == -1, "last call expires");
    CHECK(botChatSay(now, -1, 1, 0, one, &c1, 0) == 0 && botChatSay(now, 1, 9, 0, one, &c1, 0) == 0 && botChatSay(now, 1, 1, 0, 9999, &c1, 0) == 0, "bad input");
    char cl[32]; botChatClean("^1the  ^7OLD   DEPOT.", cl, sizeof(cl), 1); CHECK(!strcmp(cl, "Old Depot"), "clean area: '%s'", cl);
    botChatClean("A", cl, sizeof(cl), 1); CHECK(!strcmp(cl, "A"), "short caps kept: '%s'", cl);
    botChatClean("say \"hi\"; quit %s", cl, sizeof(cl), 0); CHECK(!strpbrk(cl, "\";%"), "no command characters: '%s'", cl);
    CHECK(botChatLoad("garbage\n", 8) < 0 && !botChat.loaded, "bad file rejected");
    printf("%d checks, %d failed\n", checks, fails);
    return fails ? 1 : 0;
}
