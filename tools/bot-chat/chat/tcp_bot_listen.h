/* tcp_bot_listen.h: understand what a human types to the bots.
 *
 * Turns a chat line ("viper hold", "bots push A", "smoke mid pls", "are you a bot?", "ty") into an intent,
 * who it is for and which area it names. Keyword matching only, done locally: no language model, nothing
 * leaves the server. Self-contained C99, no allocation.
 *
 *   botlisten_t r;
 *   if (botListenParse(text, botNames, numBots, areaNames, numAreas, &r)) { ... r.intent, r.target, r.area ... }
 *   const char *key = botListenReplyKey(r.intent, canDo);    reply situation in the phrase bank
 *
 * The parser never decides whether a bot obeys. It reports `addressed`:
 *   BOTLISTEN_NAMED  the line names a bot ("viper hold")            -> that bot answers
 *   BOTLISTEN_GROUP  it says bots / team / all / guys / everyone    -> nearby free bots answer
 *   BOTLISTEN_NONE   nobody is addressed ("push a")                 -> obey only for a squad leader, or ignore
 * Social lines (thanks, gg, hi) and questions are meant for whoever fits; the caller picks one bot to answer.
 */
#ifndef TCP_BOT_LISTEN_H
#define TCP_BOT_LISTEN_H

#include <string.h>

enum {
    BL_NONE,
    /* orders */
    BL_FOLLOW, BL_HOLD, BL_PUSH, BL_GOTO, BL_REGROUP, BL_COVER, BL_WATCH, BL_SMOKE, BL_FLASH, BL_FRAG,
    BL_DROP_BOMB, BL_TAKE_BOMB, BL_PLANT, BL_DEFUSE, BL_SPREAD, BL_QUIET, BL_FLANK, BL_WAIT, BL_FALLBACK,
    BL_LEAD, BL_STACK, BL_CANCEL, BL_HELP,
    /* questions */
    BL_ASK_STATUS, BL_ASK_COUNT, BL_ASK_BOMB, BL_ASK_BOT, BL_ASK_OTHER,
    /* social */
    BL_THANKS, BL_SORRY, BL_GREETING, BL_BYE, BL_GG, BL_GLHF, BL_COMPLIMENT, BL_INSULT, BL_BLAME, BL_LAUGH, BL_NICE_TRY,
    BL_NAME_ONLY,
    BL_COUNT
};
enum { BOTLISTEN_NONE, BOTLISTEN_GROUP, BOTLISTEN_NAMED };

typedef struct {
    int intent;       /* BL_* */
    int addressed;    /* BOTLISTEN_* */
    int target;       /* index into botNames when addressed == BOTLISTEN_NAMED, else -1 */
    int area;         /* index into areaNames, or -1 */
    int negated;      /* the line said don't / stop / no ... */
} botlisten_t;

#define BL_ORDER(i)    ((i) >= BL_FOLLOW && (i) <= BL_HELP)
#define BL_QUESTION(i) ((i) >= BL_ASK_STATUS && (i) <= BL_ASK_OTHER)
#define BL_SOCIAL(i)   ((i) >= BL_THANKS && (i) <= BL_NICE_TRY)

static const char *const botListenNames[BL_COUNT] = {
    "none", "follow", "hold", "push", "goto", "regroup", "cover", "watch", "smoke", "flash", "frag",
    "drop_bomb", "take_bomb", "plant", "defuse", "spread", "quiet", "flank", "wait", "fallback",
    "lead", "stack", "cancel", "help",
    "ask_status", "ask_count", "ask_bomb", "ask_bot", "ask_other",
    "thanks", "sorry", "greeting", "bye", "gg", "glhf", "compliment", "insult", "blame", "laugh", "nice_try",
    "name_only"
};

/* Phrases are matched on whole words after clean-up. Longer phrases win. A few Dutch, French and German
 * words are included because that is who plays here. */
static const struct { unsigned char intent; const char *phrase; } botListenTable[] = {
    { BL_ASK_BOT, "are you a bot" }, { BL_ASK_BOT, "are you bots" }, { BL_ASK_BOT, "are you bot" }, { BL_ASK_BOT, "r u a bot" }, { BL_ASK_BOT, "u a bot" },
    { BL_ASK_BOT, "you a bot" }, { BL_ASK_BOT, "is this a bot" }, { BL_ASK_BOT, "are these bots" }, { BL_ASK_BOT, "bot or human" }, { BL_ASK_BOT, "are you real" },
    { BL_ASK_BOT, "are you human" }, { BL_ASK_BOT, "ben je een bot" }, { BL_ASK_BOT, "es tu un bot" }, { BL_ASK_BOT, "bist du ein bot" },
    { BL_ASK_STATUS, "where are you" }, { BL_ASK_STATUS, "where r u" }, { BL_ASK_STATUS, "where u at" }, { BL_ASK_STATUS, "where you at" }, { BL_ASK_STATUS, "your position" },
    { BL_ASK_STATUS, "status" }, { BL_ASK_STATUS, "what are you doing" }, { BL_ASK_STATUS, "waar ben je" }, { BL_ASK_STATUS, "ou es tu" }, { BL_ASK_STATUS, "wo bist du" },
    { BL_ASK_COUNT, "how many" }, { BL_ASK_COUNT, "how much left" }, { BL_ASK_COUNT, "hoeveel" }, { BL_ASK_COUNT, "combien" }, { BL_ASK_COUNT, "wie viele" },
    { BL_ASK_BOMB, "who has the bomb" }, { BL_ASK_BOMB, "who has bomb" }, { BL_ASK_BOMB, "whos got the bomb" }, { BL_ASK_BOMB, "where is the bomb" }, { BL_ASK_BOMB, "wheres the bomb" },
    { BL_ASK_BOMB, "where bomb" }, { BL_ASK_BOMB, "wheres bomb" }, { BL_ASK_BOMB, "who bomb" }, { BL_ASK_BOMB, "bomb where" }, { BL_ASK_BOMB, "wie heeft de bom" },
    { BL_ASK_OTHER, "where are they" }, { BL_ASK_OTHER, "where is he" }, { BL_ASK_OTHER, "wheres he" }, { BL_ASK_OTHER, "any info" }, { BL_ASK_OTHER, "info" }, { BL_ASK_OTHER, "seen anyone" },

    { BL_DROP_BOMB, "drop the bomb" }, { BL_DROP_BOMB, "drop bomb" }, { BL_DROP_BOMB, "give me the bomb" }, { BL_DROP_BOMB, "give bomb" }, { BL_DROP_BOMB, "drop it" }, { BL_DROP_BOMB, "bomb to me" },
    { BL_TAKE_BOMB, "take the bomb" }, { BL_TAKE_BOMB, "take bomb" }, { BL_TAKE_BOMB, "get the bomb" }, { BL_TAKE_BOMB, "get bomb" }, { BL_TAKE_BOMB, "pick up the bomb" },
    { BL_TAKE_BOMB, "grab the bomb" }, { BL_TAKE_BOMB, "grab bomb" }, { BL_TAKE_BOMB, "carry the bomb" }, { BL_TAKE_BOMB, "pak de bom" },
    { BL_PLANT, "plant" }, { BL_PLANT, "plant the bomb" }, { BL_PLANT, "plant it" }, { BL_PLANT, "plant here" },
    { BL_DEFUSE, "defuse" }, { BL_DEFUSE, "defuse it" }, { BL_DEFUSE, "defuse the bomb" }, { BL_DEFUSE, "get on the bomb" }, { BL_DEFUSE, "ontmantel" },
    { BL_FOLLOW, "follow me" }, { BL_FOLLOW, "follow" }, { BL_FOLLOW, "with me" }, { BL_FOLLOW, "on me" }, { BL_FOLLOW, "come with me" }, { BL_FOLLOW, "stay with me" },
    { BL_FOLLOW, "come here" }, { BL_FOLLOW, "come" }, { BL_FOLLOW, "volg mij" }, { BL_FOLLOW, "volg" }, { BL_FOLLOW, "suis moi" }, { BL_FOLLOW, "folg mir" }, { BL_FOLLOW, "kom" },
    { BL_HOLD, "hold" }, { BL_HOLD, "hold here" }, { BL_HOLD, "hold position" }, { BL_HOLD, "hold this" }, { BL_HOLD, "stay" }, { BL_HOLD, "stay here" }, { BL_HOLD, "stay there" },
    { BL_HOLD, "hold site" }, { BL_HOLD, "defend" }, { BL_HOLD, "camp" }, { BL_HOLD, "blijf" }, { BL_HOLD, "blijf hier" }, { BL_HOLD, "reste" }, { BL_HOLD, "reste ici" }, { BL_HOLD, "bleib" },
    { BL_PUSH, "push" }, { BL_PUSH, "push now" }, { BL_PUSH, "rush" }, { BL_PUSH, "go go" }, { BL_PUSH, "go go go" }, { BL_PUSH, "attack" }, { BL_PUSH, "charge" }, { BL_PUSH, "lets go" },
    { BL_PUSH, "move up" }, { BL_PUSH, "go in" }, { BL_PUSH, "all in" }, { BL_PUSH, "aanvallen" }, { BL_PUSH, "allez" }, { BL_PUSH, "los" }, { BL_PUSH, "execute" },
    { BL_GOTO, "go" }, { BL_GOTO, "go to" }, { BL_GOTO, "move to" }, { BL_GOTO, "take" }, { BL_GOTO, "rotate" }, { BL_GOTO, "rotate to" }, { BL_GOTO, "head to" }, { BL_GOTO, "ga naar" }, { BL_GOTO, "va a" },
    { BL_REGROUP, "regroup" }, { BL_REGROUP, "group up" }, { BL_REGROUP, "group" }, { BL_REGROUP, "together" }, { BL_REGROUP, "stick together" }, { BL_REGROUP, "come back" }, { BL_REGROUP, "gather" },
    { BL_COVER, "cover me" }, { BL_COVER, "cover" }, { BL_COVER, "watch my back" }, { BL_COVER, "protect me" }, { BL_COVER, "dek mij" }, { BL_COVER, "couvre moi" },
    { BL_WATCH, "watch" }, { BL_WATCH, "look at" }, { BL_WATCH, "check" }, { BL_WATCH, "guard" }, { BL_WATCH, "eyes on" }, { BL_WATCH, "keep an eye on" },
    { BL_SMOKE, "smoke" }, { BL_SMOKE, "throw smoke" }, { BL_SMOKE, "need smoke" }, { BL_SMOKE, "rook" }, { BL_SMOKE, "fumee" },
    { BL_FLASH, "flash" }, { BL_FLASH, "flash me" }, { BL_FLASH, "throw flash" }, { BL_FLASH, "stun" }, { BL_FLASH, "flashbang" }, { BL_FLASH, "blind them" },
    { BL_FRAG, "nade" }, { BL_FRAG, "grenade" }, { BL_FRAG, "frag" }, { BL_FRAG, "throw nade" }, { BL_FRAG, "nade it" }, { BL_FRAG, "granaat" },
    { BL_SPREAD, "spread" }, { BL_SPREAD, "spread out" }, { BL_SPREAD, "split" }, { BL_SPREAD, "split up" }, { BL_SPREAD, "dont stack" }, { BL_SPREAD, "verspreid" },
    { BL_QUIET, "quiet" }, { BL_QUIET, "walk" }, { BL_QUIET, "shh" }, { BL_QUIET, "silent" }, { BL_QUIET, "sneak" }, { BL_QUIET, "be quiet" }, { BL_QUIET, "stop running" }, { BL_QUIET, "no noise" }, { BL_QUIET, "stil" },
    { BL_FLANK, "flank" }, { BL_FLANK, "go around" }, { BL_FLANK, "go round" }, { BL_FLANK, "go behind" }, { BL_FLANK, "behind them" }, { BL_FLANK, "lurk" },
    { BL_WAIT, "wait" }, { BL_WAIT, "wait for me" }, { BL_WAIT, "hold on" }, { BL_WAIT, "not yet" }, { BL_WAIT, "wacht" }, { BL_WAIT, "attends" }, { BL_WAIT, "warte" }, { BL_WAIT, "slow down" },
    { BL_FALLBACK, "fall back" }, { BL_FALLBACK, "fallback" }, { BL_FALLBACK, "back" }, { BL_FALLBACK, "back off" }, { BL_FALLBACK, "retreat" }, { BL_FALLBACK, "get back" }, { BL_FALLBACK, "get out" }, { BL_FALLBACK, "terug" }, { BL_FALLBACK, "save" },
    { BL_LEAD, "lead" }, { BL_LEAD, "go first" }, { BL_LEAD, "you first" }, { BL_LEAD, "you go first" }, { BL_LEAD, "entry" }, { BL_LEAD, "take point" },
    { BL_STACK, "stack" }, { BL_STACK, "all" }, { BL_STACK, "everyone to" }, { BL_STACK, "everyone" }, { BL_STACK, "all go" },
    { BL_CANCEL, "cancel" }, { BL_CANCEL, "never mind" }, { BL_CANCEL, "nevermind" }, { BL_CANCEL, "nvm" }, { BL_CANCEL, "forget it" }, { BL_CANCEL, "as you were" }, { BL_CANCEL, "do your thing" },
    { BL_CANCEL, "stop following" }, { BL_CANCEL, "free" }, { BL_CANCEL, "laat maar" },
    { BL_HELP, "help" }, { BL_HELP, "help me" }, { BL_HELP, "need help" }, { BL_HELP, "need backup" }, { BL_HELP, "backup" }, { BL_HELP, "save me" }, { BL_HELP, "hulp" }, { BL_HELP, "aide" }, { BL_HELP, "hilfe" },

    { BL_THANKS, "thanks" }, { BL_THANKS, "thank you" }, { BL_THANKS, "thx" }, { BL_THANKS, "ty" }, { BL_THANKS, "tyvm" }, { BL_THANKS, "cheers" }, { BL_THANKS, "merci" }, { BL_THANKS, "danke" }, { BL_THANKS, "bedankt" }, { BL_THANKS, "dank je" }, { BL_THANKS, "dankje" },
    { BL_SORRY, "sorry" }, { BL_SORRY, "sry" }, { BL_SORRY, "my bad" }, { BL_SORRY, "mb" }, { BL_SORRY, "oops" }, { BL_SORRY, "pardon" }, { BL_SORRY, "desole" },
    { BL_GREETING, "hi" }, { BL_GREETING, "hello" }, { BL_GREETING, "hey" }, { BL_GREETING, "yo" }, { BL_GREETING, "hallo" }, { BL_GREETING, "hoi" }, { BL_GREETING, "salut" }, { BL_GREETING, "bonjour" }, { BL_GREETING, "sup" }, { BL_GREETING, "hi all" }, { BL_GREETING, "hey all" }, { BL_GREETING, "goedenavond" }, { BL_GREETING, "moin" },
    { BL_BYE, "bye" }, { BL_BYE, "cya" }, { BL_BYE, "bb" }, { BL_BYE, "gtg" }, { BL_BYE, "good night" }, { BL_BYE, "gn" }, { BL_BYE, "see you" }, { BL_BYE, "later" }, { BL_BYE, "doei" }, { BL_BYE, "a plus" }, { BL_BYE, "tschuss" }, { BL_BYE, "im off" },
    { BL_GG, "gg" }, { BL_GG, "ggs" }, { BL_GG, "gg wp" }, { BL_GG, "good game" }, { BL_GG, "wp" }, { BL_GG, "ggwp" },
    { BL_GLHF, "glhf" }, { BL_GLHF, "gl hf" }, { BL_GLHF, "gl" }, { BL_GLHF, "hf" }, { BL_GLHF, "good luck" }, { BL_GLHF, "have fun" }, { BL_GLHF, "succes" }, { BL_GLHF, "bonne chance" },
    { BL_COMPLIMENT, "nice" }, { BL_COMPLIMENT, "nice shot" }, { BL_COMPLIMENT, "ns" }, { BL_COMPLIMENT, "gj" }, { BL_COMPLIMENT, "good job" }, { BL_COMPLIMENT, "well played" }, { BL_COMPLIMENT, "nice one" },
    { BL_COMPLIMENT, "good bot" }, { BL_COMPLIMENT, "nice bot" }, { BL_COMPLIMENT, "well done" }, { BL_COMPLIMENT, "great" }, { BL_COMPLIMENT, "sick" }, { BL_COMPLIMENT, "goed gedaan" }, { BL_COMPLIMENT, "bien joue" },
    { BL_INSULT, "noob" }, { BL_INSULT, "noobs" }, { BL_INSULT, "useless" }, { BL_INSULT, "stupid" }, { BL_INSULT, "dumb" }, { BL_INSULT, "trash" }, { BL_INSULT, "bad bot" }, { BL_INSULT, "stupid bot" }, { BL_INSULT, "stupid bots" },
    { BL_INSULT, "useless bots" }, { BL_INSULT, "idiot" }, { BL_INSULT, "idiots" }, { BL_INSULT, "you suck" }, { BL_INSULT, "bots suck" }, { BL_INSULT, "so bad" }, { BL_INSULT, "dom" }, { BL_INSULT, "nul" },
    { BL_BLAME, "your fault" }, { BL_BLAME, "why did you" }, { BL_BLAME, "what are you doing" }, { BL_BLAME, "wtf" }, { BL_BLAME, "you lost us" }, { BL_BLAME, "thanks for nothing" }, { BL_BLAME, "why" },
    { BL_LAUGH, "lol" }, { BL_LAUGH, "haha" }, { BL_LAUGH, "hahaha" }, { BL_LAUGH, "lmao" }, { BL_LAUGH, "xd" }, { BL_LAUGH, "rofl" }, { BL_LAUGH, "hehe" },
    { BL_NICE_TRY, "nt" }, { BL_NICE_TRY, "nice try" }, { BL_NICE_TRY, "unlucky" }, { BL_NICE_TRY, "unl" }, { BL_NICE_TRY, "so close" }, { BL_NICE_TRY, "jammer" }, { BL_NICE_TRY, "dommage" },
};
#define BOTLISTEN_TABLE ((int)(sizeof(botListenTable) / sizeof(botListenTable[0])))

/* Lower-case, drop colour codes and punctuation, collapse spaces, pad with one space each side. */
static int botListenClean(const char *in, char *out, int outLen)
{
    int n = 0; out[n++] = ' ';
    for (const char *s = in; *s && n < outLen - 2; s++) {
        unsigned char c = (unsigned char)*s;
        if (c == '^' && s[1]) { s++; continue; }
        if (c == '\'' || c == '`') continue;                          /* don't -> dont, what's -> whats */
        if (c >= 'A' && c <= 'Z') c = (unsigned char)(c + 32);
        if (c >= 0x80) {                                              /* fold the common accented letters (UTF-8 and Latin-1) */
            if (c == 0xC3 && s[1]) { unsigned char d = (unsigned char)*++s; c = (d >= 0xA8 && d <= 0xAB) ? 'e' : (d >= 0xA0 && d <= 0xA5) ? 'a' : (d >= 0xB9 && d <= 0xBC) ? 'u' : (d >= 0xB2 && d <= 0xB6) ? 'o' : (d >= 0xAC && d <= 0xAF) ? 'i' : d == 0xA7 ? 'c' : ' '; }
            else c = (c >= 0xE8 && c <= 0xEB) ? 'e' : (c >= 0xE0 && c <= 0xE5) ? 'a' : (c >= 0xF9 && c <= 0xFC) ? 'u' : (c >= 0xF2 && c <= 0xF6) ? 'o' : ' ';
        }
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9'))) c = ' ';
        if (c == ' ' && out[n - 1] == ' ') continue;
        out[n++] = (char)c;
    }
    if (out[n - 1] != ' ') out[n++] = ' ';
    out[n] = 0;
    return n;
}

/* Find " word " in the padded string; returns offset of the leading space or -1. */
static int botListenFind(const char *hay, const char *phrase)
{
    char pat[64]; size_t l = strlen(phrase);
    if (l + 3 > sizeof(pat)) return -1;
    pat[0] = ' '; memcpy(pat + 1, phrase, l); pat[l + 1] = ' '; pat[l + 2] = 0;
    const char *p = strstr(hay, pat);
    return p ? (int)(p - hay) : -1;
}
static void botListenBlank(char *hay, int at, int len) { for (int i = at + 1; i < at + 1 + len; i++) hay[i] = '_'; }

/* Parse one chat line. Returns 1 when it means something to the bots. */
static int botListenParse(const char *text, const char *const *botNames, int numBots, const char *const *areaNames, int numAreas, botlisten_t *out)
{
    char msg[160], tmp[64];
    out->intent = BL_NONE; out->addressed = BOTLISTEN_NONE; out->target = -1; out->area = -1; out->negated = 0;
    if (!text || !*text) return 0;
    int len = botListenClean(text, msg, sizeof(msg));
    if (len < 3) return 0;
    /* who is it for: a bot's name, or a group word */
    int words = 0; for (int i = 1; msg[i]; i++) if (msg[i] == ' ') words++;
    for (int b = 0; b < numBots; b++) {
        if (!botNames[b] || !botNames[b][0]) continue;
        botListenClean(botNames[b], tmp, sizeof(tmp));
        size_t tl = strlen(tmp); if (tl < 4) continue;                /* " xy " at least two letters */
        tmp[tl - 1] = 0;
        int at = botListenFind(msg, tmp + 1);
        if (at >= 0) { out->addressed = BOTLISTEN_NAMED; out->target = b; botListenBlank(msg, at, (int)tl - 2); break; }
    }
    if (out->addressed == BOTLISTEN_NONE) {
        static const char *const grp[] = { "bots", "bot", "team", "guys", "everyone", "everybody", "all bots", "you all", "jongens", "tout le monde", "alle" };
        for (int g = 0; g < (int)(sizeof(grp) / sizeof(grp[0])); g++) if (botListenFind(msg, grp[g]) >= 0) { out->addressed = BOTLISTEN_GROUP; break; }
    }
    /* which area: the longest area name that appears; a single letter or digit matches "Site A" style names */
    int bestLen = 0, bestAt = -1;
    for (int a = 0; a < numAreas; a++) {
        if (!areaNames[a] || !areaNames[a][0]) continue;
        botListenClean(areaNames[a], tmp, sizeof(tmp));
        int tl = (int)strlen(tmp); if (tl < 3) continue;
        tmp[tl - 1] = 0;
        int at = botListenFind(msg, tmp + 1);
        if (at >= 0 && tl - 2 > bestLen) { bestLen = tl - 2; bestAt = at; out->area = a; }
    }
    if (out->area < 0)
        for (int a = 0; a < numAreas && out->area < 0; a++) {
            if (!areaNames[a]) continue;
            botListenClean(areaNames[a], tmp, sizeof(tmp));
            int tl = (int)strlen(tmp);
            if (tl >= 5 && tmp[tl - 3] == ' ') {                      /* name ends in one character: "site a", "tunnel 2" */
                char one[2] = { tmp[tl - 2], 0 };
                int at = botListenFind(msg, one);
                /* only as the last word, so "take a look" is not Site A */
                if (at >= 0 && msg[at + 3] == 0) { out->area = a; bestAt = at; bestLen = 1; }
            }
        }
    if (bestAt >= 0) botListenBlank(msg, bestAt, bestLen);
    /* negation */
    static const char *const neg[] = { "dont", "do not", "stop", "no", "not", "niet", "ne pas", "nicht" };
    for (int i = 0; i < (int)(sizeof(neg) / sizeof(neg[0])); i++) if (botListenFind(msg, neg[i]) >= 0) out->negated = 1;
    /* intent: longest phrase wins, earlier table rows win ties */
    int best = -1; size_t bl = 0;
    for (int i = 0; i < BOTLISTEN_TABLE; i++) {
        size_t l = strlen(botListenTable[i].phrase);
        if (l > bl && botListenFind(msg, botListenTable[i].phrase) >= 0) { best = i; bl = l; }
    }
    if (best >= 0) out->intent = botListenTable[best].intent;
    /* fix-ups */
    if (out->intent == BL_GOTO && out->area < 0) out->intent = BL_PUSH;              /* "go" with no place is "go!" */
    if (out->intent == BL_STACK && out->area < 0) out->intent = BL_REGROUP;          /* "everyone" with no place */
    if ((out->intent == BL_PUSH || out->intent == BL_HOLD) && out->area >= 0 && botListenFind(msg, "all") >= 0) out->intent = BL_STACK;
    if (out->intent == BL_NONE && out->area >= 0 && out->addressed != BOTLISTEN_NONE) out->intent = BL_GOTO;   /* "viper tunnel" */
    if (out->intent == BL_NONE && out->addressed == BOTLISTEN_NAMED && words <= 1) out->intent = BL_NAME_ONLY;
    if (out->intent == BL_NONE && out->addressed != BOTLISTEN_NONE && strchr(text, '?')) out->intent = BL_ASK_OTHER;
    if (out->negated && BL_ORDER(out->intent)) {
        if (out->intent == BL_PUSH || out->intent == BL_GOTO || out->intent == BL_LEAD || out->intent == BL_FLANK) out->intent = BL_WAIT;
        else if (out->intent == BL_HOLD || out->intent == BL_WAIT || out->intent == BL_QUIET) out->intent = BL_PUSH;
        else if (out->intent != BL_SPREAD && out->intent != BL_CANCEL) out->intent = BL_CANCEL;      /* "dont stack" is already spread */
    }
    /* Ordinary chat is full of words like "back", "take", "later" and "nice". When nobody is addressed, only a short
     * line counts: an order without a place needs to be 4 words or fewer, a social line too. */
    if (out->addressed == BOTLISTEN_NONE && words > 4 && ((BL_ORDER(out->intent) && out->area < 0) || BL_SOCIAL(out->intent))) out->intent = BL_NONE;
    return out->intent != BL_NONE;
}

/* The phrase-bank situation a bot answers with. `can` = the bot can do it (has the grenade, is alive, is free). */
static const char *botListenReplyKey(int intent, int can)
{
    switch (intent) {
    case BL_FOLLOW: return can ? "order_follow" : "order_busy";
    case BL_HOLD: return can ? "order_hold" : "order_busy";
    case BL_PUSH: return can ? "order_push" : "order_busy";
    case BL_GOTO: return can ? "order_goto" : "order_too_far";
    case BL_REGROUP: return can ? "order_regroup" : "order_too_far";
    case BL_COVER: return can ? "order_cover_me" : "order_too_far";
    case BL_WATCH: return can ? "order_watch" : "order_busy";
    case BL_SMOKE: return can ? "order_smoke" : "order_no_utility";
    case BL_FLASH: return can ? "order_flash" : "order_no_utility";
    case BL_FRAG: return can ? "order_frag" : "order_no_utility";
    case BL_DROP_BOMB: return can ? "order_drop_bomb" : "ask_unknown_reply";
    case BL_TAKE_BOMB: return can ? "order_take_bomb" : "order_too_far";
    case BL_PLANT: return can ? "order_plant" : "order_busy";
    case BL_DEFUSE: return can ? "order_defuse" : "order_busy";
    case BL_SPREAD: return "order_spread";
    case BL_QUIET: return "order_quiet";
    case BL_FLANK: return can ? "order_flank" : "order_busy";
    case BL_WAIT: return "order_wait";
    case BL_FALLBACK: return "order_fallback";
    case BL_LEAD: return can ? "order_lead" : "order_busy";
    case BL_STACK: return can ? "order_stack" : "order_too_far";
    case BL_CANCEL: return "ping_cancel";
    case BL_HELP: return can ? "ping_help_ack" : "fu_cant_help";
    case BL_ASK_STATUS: return "ask_status_reply";
    case BL_ASK_COUNT: return can ? "ask_count_reply" : "ask_unknown_reply";
    case BL_ASK_BOMB: return can ? "ask_bomb_reply" : "ask_unknown_reply";
    case BL_ASK_BOT: return "reply_are_you_bot";
    case BL_ASK_OTHER: return can ? "fu_answer_ask_info" : "reply_question_generic";
    case BL_THANKS: return "reply_thanks";
    case BL_SORRY: return "reply_sorry";
    case BL_GREETING: return "reply_greeting";
    case BL_BYE: return "reply_bye";
    case BL_GG: return "reply_gg";
    case BL_GLHF: return "reply_glhf";
    case BL_COMPLIMENT: return "reply_compliment";
    case BL_INSULT: return "reply_insult";
    case BL_BLAME: return "reply_blame";
    case BL_LAUGH: return "reply_laugh";
    case BL_NICE_TRY: return "reply_nice_try";
    case BL_NAME_ONLY: return "called_by_name";
    default: return NULL;
    }
}

#endif /* TCP_BOT_LISTEN_H */
