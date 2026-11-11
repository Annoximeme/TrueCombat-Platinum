/* tcp_bot_chat.h: bot chat lines from the offline phrase bank (bots-brain/phrases/phrases.txt).
 *
 * Self-contained C99, no engine includes, no allocation after botChatLoad. The game module does the
 * file I/O and the sending; this file parses the bank, picks lines and paces them.
 *
 *   botChatLoad(text, len)                 parse phrases.txt once at map load (text may be freed after)
 *   botChatSituation("contact_one")        key -> id, resolve once and cache
 *   botChatSay(now, slot, team, pers, sit, &ctx, flags)   ask for a line; returns 1 if queued
 *   botChatFrame(now, emit)                call every server frame; emits lines that are due
 *   botChatCancel(slot, sit)               drop a queued line that went stale (enemy died, area cleared)
 *   botChatRoundReset()                    call at round start
 *   botChatSetVoice(slot, chatty, lower)   per-bot chattiness and typing style from the roster
 *
 * Pacing and picking follow the README: typing delay, one line per team every 1.5 s, three per bot
 * per 10 s, per-situation cooldowns, chattiness per personality, an 8-line no-repeat window per team
 * and situation, lines whose placeholders can't be filled are skipped, area names are cleaned, and a
 * quarter of the lines are lower-cased. Orders (BOTCHAT_FORCE) skip chattiness and the bot cap.
 * Contact and objective calls get a chattiness floor of 75%, so quiet bots still report what matters.
 *
 * Replies to another line (fu_ack_teammate_call, fu_thanks_teammate) must be requested from the emit
 * callback of the line they answer, never when that line is queued, or the answer can appear first.
 */
#ifndef TCP_BOT_CHAT_H
#define TCP_BOT_CHAT_H

#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#ifndef BOTCHAT_MAX_SLOTS
#define BOTCHAT_MAX_SLOTS 64
#endif
#define BOTCHAT_MAX_TEAMS 4
#define BOTCHAT_MAX_SITS 512
#define BOTCHAT_MAX_LINES 16384
#define BOTCHAT_ARENA (384 * 1024)
#define BOTCHAT_KEYLEN 32
#define BOTCHAT_WINDOW 8
#define BOTCHAT_QUEUE 32
#define BOTCHAT_MAX_TEXT 64      /* filled lines longer than this are skipped */
#define BOTCHAT_OUT 128

enum { BOTCHAT_ENTRY, BOTCHAT_ANCHOR, BOTCHAT_LURKER, BOTCHAT_SUPPORT, BOTCHAT_MARKSMAN, BOTCHAT_PERS };
enum { BOTCHAT_TEAM = 0, BOTCHAT_ALL = 1 };
enum { BOTCHAT_FORCE = 1,        /* reply to an order or ping: always answered */
       BOTCHAT_NODELAY = 2,      /* no typing delay (death info, grenade warnings) */
       BOTCHAT_DEAD = 4 };       /* speaker is dead: caller must only pass dead-allowed situations */
enum { BOTCHAT_F_AREA = 1, BOTCHAT_F_COUNT = 2, BOTCHAT_F_NAME = 4, BOTCHAT_F_ENEMY = 8 };

typedef struct { const char *area; int count; const char *name; const char *enemy; } botchat_ctx_t;
typedef void (*botchat_emit_t)(int slot, int team, int channel, int sit, const char *text);

typedef struct {
    char key[BOTCHAT_KEYLEN];
    unsigned char channel, group;
    int cooldownMs;
    int first[BOTCHAT_PERS], count[BOTCHAT_PERS];
} botchat_sit_t;

typedef struct { int dueAt, slot, team, sit, channel; char text[BOTCHAT_OUT]; } botchat_q_t;

static struct {
    int loaded, numSits, numLines, arenaUsed;
    botchat_sit_t sits[BOTCHAT_MAX_SITS];
    const char *line[BOTCHAT_MAX_LINES];
    unsigned char lineFlags[BOTCHAT_MAX_LINES];
    short hash[1024];
    char arena[BOTCHAT_ARENA];
    /* runtime */
    unsigned seed;
    int mode;                                         /* bot_chat cvar: 0 off, 1 team only, 2 team and all */
    short recent[BOTCHAT_MAX_SITS][BOTCHAT_MAX_TEAMS][BOTCHAT_WINDOW];
    int teamNext[BOTCHAT_MAX_TEAMS];                  /* earliest time the next line may be emitted */
    int botTimes[BOTCHAT_MAX_SLOTS][3];               /* last three emit times per bot */
    int botSitAt[BOTCHAT_MAX_SLOTS][8][2];            /* small per-bot cooldown table: sit, until */
    int lastSit[BOTCHAT_MAX_SLOTS], lastAt[BOTCHAT_MAX_SLOTS];
    char lastArea[BOTCHAT_MAX_SLOTS][32];
    signed char voiceChatty[BOTCHAT_MAX_SLOTS];       /* per-bot chattiness from the roster, -1 = personality default */
    unsigned char voiceLower[BOTCHAT_MAX_SLOTS];       /* percent of lines typed lower-case */
    botchat_q_t q[BOTCHAT_QUEUE]; int qn;
    int said, dropped, why[8];   /* why: 1 typing, 2 chattiness, 3 bot cap, 4 cooldown, 5 queue full, 6 stale, 7 no line fits */
} botChat;

static const char *const botChatPersNames[BOTCHAT_PERS] = { "entry", "anchor", "lurker", "support", "marksman" };
static const char *const botChatGroups[] = { "contact", "action", "damage", "objective", "clutch", "round", "orders", "followup" };
/* Chance (percent) that a chosen bot actually speaks. */
static const int botChatChatty[BOTCHAT_PERS] = { 80, 60, 35, 80, 45 };

static unsigned botChatRand(void)
{
    botChat.seed = botChat.seed * 1664525u + 1013904223u;
    return (botChat.seed >> 8) & 0xffffff;
}
static unsigned botChatHashKey(const char *s)
{
    unsigned h = 2166136261u;
    for (; *s; s++) h = (h ^ (unsigned char)*s) * 16777619u;
    return h & 1023;
}

/* Key -> situation id, or -1. */
static int botChatSituation(const char *key)
{
    if (!botChat.loaded) return -1;
    for (unsigned h = botChatHashKey(key), n = 0; n < 1024; n++, h = (h + 1) & 1023) {
        int i = botChat.hash[h];
        if (i < 0) return -1;
        if (!strcmp(botChat.sits[i].key, key)) return i;
    }
    return -1;
}

static int botChatPersonality(const char *name)
{
    for (int i = 0; i < BOTCHAT_PERS; i++) if (!strcmp(name, botChatPersNames[i])) return i;
    return -1;
}

static void botChatRoundReset(void)
{
    botChat.qn = 0;
    memset(botChat.teamNext, 0, sizeof(botChat.teamNext));
    memset(botChat.botSitAt, 0, sizeof(botChat.botSitAt));
    for (int i = 0; i < BOTCHAT_MAX_SLOTS; i++) { botChat.lastSit[i] = -1; botChat.lastArea[i][0] = 0; botChat.botTimes[i][0] = botChat.botTimes[i][1] = botChat.botTimes[i][2] = -1000000; }
}

/* Parse phrases.txt. Returns the number of lines loaded, or a negative error:
 * -1 too many situations, -2 too many lines, -3 arena full, -4 bad row, -5 unknown situation or personality. */
static int botChatLoad(const char *text, int len)
{
    const char *p = text, *end = text + len;
    int curSit = -1, curPers = -1;
    botChat.loaded = 0; botChat.numSits = botChat.numLines = botChat.arenaUsed = 0;
    botChat.mode = 2; if (!botChat.seed) botChat.seed = 0x7c0ffee;
    memset(botChat.hash, 0xff, sizeof(botChat.hash));
    memset(botChat.recent, 0xff, sizeof(botChat.recent));
    for (int i = 0; i < BOTCHAT_MAX_SLOTS; i++) { botChat.botTimes[i][0] = botChat.botTimes[i][1] = botChat.botTimes[i][2] = -1000000; botChat.voiceChatty[i] = -1; botChat.voiceLower[i] = 25; }
    while (p < end) {
        const char *eol = memchr(p, '\n', (size_t)(end - p)); if (!eol) eol = end;
        const char *e = eol; if (e > p && e[-1] == '\r') e--;
        const char *f[6]; int fl[6], nf = 0;
        if (e > p && *p != '#') {
            const char *s = p;
            while (nf < 6) {                                      /* split on TAB; last field keeps the rest */
                const char *t = (nf < 5) ? memchr(s, '\t', (size_t)(e - s)) : NULL;
                f[nf] = s; fl[nf] = (int)((t ? t : e) - s); nf++;
                if (!t) break;
                s = t + 1;
            }
            if (*p == '@') {
                if (nf < 4 || fl[0] < 2 || fl[0] > BOTCHAT_KEYLEN) return -4;
                if (botChat.numSits >= BOTCHAT_MAX_SITS) return -1;
                botchat_sit_t *st = &botChat.sits[botChat.numSits];
                memset(st, 0, sizeof(*st));
                memcpy(st->key, f[0] + 1, (size_t)fl[0] - 1);
                for (int g = 0; g < (int)(sizeof(botChatGroups) / sizeof(botChatGroups[0])); g++)
                    if ((int)strlen(botChatGroups[g]) == fl[1] && !memcmp(botChatGroups[g], f[1], (size_t)fl[1])) st->group = (unsigned char)g;
                st->channel = (fl[2] == 3 && !memcmp(f[2], "all", 3)) ? BOTCHAT_ALL : BOTCHAT_TEAM;
                st->cooldownMs = atoi(f[3]) * 1000;
                unsigned h = botChatHashKey(st->key);
                while (botChat.hash[h] >= 0) h = (h + 1) & 1023;
                botChat.hash[h] = (short)botChat.numSits;
                curSit = botChat.numSits++; curPers = -1;
            } else {
                char key[BOTCHAT_KEYLEN + 1], pers[16];
                if (nf < 3 || fl[0] > BOTCHAT_KEYLEN || fl[1] > 15 || fl[2] < 1) return -4;
                /* a text row may itself contain no further tabs; rejoin anything split past field 2 */
                int tl = (int)(e - f[2]);
                memcpy(key, f[0], (size_t)fl[0]); key[fl[0]] = 0;
                memcpy(pers, f[1], (size_t)fl[1]); pers[fl[1]] = 0;
                int pi = botChatPersonality(pers);
                if (curSit < 0 || pi < 0 || strcmp(botChat.sits[curSit].key, key)) return -5;
                if (pi < curPers) return -5;                      /* rows must be grouped by personality */
                if (botChat.numLines >= BOTCHAT_MAX_LINES) return -2;
                if (botChat.arenaUsed + tl + 1 > BOTCHAT_ARENA) return -3;
                char *dst = botChat.arena + botChat.arenaUsed;
                memcpy(dst, f[2], (size_t)tl); dst[tl] = 0; botChat.arenaUsed += tl + 1;
                unsigned char flags = 0;
                if (strstr(dst, "{area}")) flags |= BOTCHAT_F_AREA;
                if (strstr(dst, "{count}")) flags |= BOTCHAT_F_COUNT;
                if (strstr(dst, "{name}")) flags |= BOTCHAT_F_NAME;
                if (strstr(dst, "{enemy}")) flags |= BOTCHAT_F_ENEMY;
                botchat_sit_t *st = &botChat.sits[curSit];
                if (!st->count[pi]) st->first[pi] = botChat.numLines;
                st->count[pi]++; curPers = pi;
                botChat.lineFlags[botChat.numLines] = flags;
                botChat.line[botChat.numLines++] = dst;
            }
        }
        p = eol + 1;
    }
    botChat.loaded = botChat.numLines > 0;
    botChatRoundReset();
    return botChat.numLines;
}

/* Clean a location or player name for chat: strip ^x colour codes and control characters, trim,
 * drop a leading article and fix ALL CAPS (area names only). */
static void botChatClean(const char *in, char *out, int outLen, int isArea)
{
    int n = 0, letters = 0, upper = 0;
    if (!in) in = "";
    for (const char *s = in; *s && n < outLen - 1; s++) {
        if (*s == '^' && s[1]) { s++; continue; }
        unsigned char c = (unsigned char)*s;
        if (c < 32 || c == '"' || c == ';' || c == '%' || c == '{' || c == '}') c = ' ';
        if (c == ' ' && (n == 0 || out[n - 1] == ' ')) continue;
        out[n++] = (char)c;
    }
    while (n > 0 && strchr(" .,:;-_", out[n - 1])) n--;
    out[n] = 0;
    if (!isArea) return;
    static const char *const art[] = { "the ", "a ", "an " };
    for (int i = 0; i < 3; i++) {
        size_t l = strlen(art[i]);
        if ((size_t)n > l) {
            int same = 1;
            for (size_t k = 0; k < l; k++) { char c = out[k]; if (c >= 'A' && c <= 'Z') c += 32; if (c != art[i][k]) same = 0; }
            if (same) { memmove(out, out + l, (size_t)n - l + 1); n -= (int)l; break; }
        }
    }
    for (int i = 0; i < n; i++) { char c = out[i]; if (c >= 'a' && c <= 'z') letters++; else if (c >= 'A' && c <= 'Z') { letters++; upper++; } }
    if (n > 3 && letters && upper == letters)
        for (int i = 0, start = 1; i < n; i++) {
            char c = out[i];
            if (c >= 'A' && c <= 'Z') { if (!start) out[i] = (char)(c + 32); start = 0; } else start = (c == ' ');
        }
}

static int botChatLower(int c) { return (c >= 'A' && c <= 'Z') ? c + 32 : c; }
static int botChatAlnum(int c) { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9'); }

/* 1 when a landmark word of the area name already appears in the line ("he's on the roof" + "Roof"). */
static int botChatAreaClash(const char *line, const char *area)
{
    static const char *const marks[] = { "roof", "window", "ladder", "door", "spawn", "bomb", "site", "stairs", "water", "smoke", "back", "top", "long", "mid" };
    for (int m = 0; m < (int)(sizeof(marks) / sizeof(marks[0])); m++) {
        size_t l = strlen(marks[m]); int inArea = 0, inLine = 0;
        for (int pass = 0; pass < 2; pass++) {
            const char *s = pass ? line : area;
            for (const char *w = s; *w; w++) {
                if (w != s && botChatAlnum((unsigned char)w[-1])) continue;
                size_t k = 0; while (k < l && botChatLower((unsigned char)w[k]) == marks[m][k]) k++;
                if (k == l && !botChatAlnum((unsigned char)w[l])) { if (pass) inLine = 1; else inArea = 1; }
            }
        }
        if (inArea && inLine) return 1;
    }
    return 0;
}

/* Fill placeholders. Returns length, or -1 when it does not fit. */
static int botChatFill(const char *line, const char *area, int count, const char *name, const char *enemy, char *out, int outLen)
{
    int n = 0;
    for (const char *s = line; *s; ) {
        const char *rep = NULL; char num[12]; int skip = 0;
        if (*s == '{') {
            if (!strncmp(s, "{area}", 6)) { rep = area; skip = 6; }
            else if (!strncmp(s, "{count}", 7)) { snprintf(num, sizeof(num), "%d", count); rep = num; skip = 7; }
            else if (!strncmp(s, "{name}", 6)) { rep = name; skip = 6; }
            else if (!strncmp(s, "{enemy}", 7)) { rep = enemy; skip = 7; }
        }
        if (rep) { int l = (int)strlen(rep); if (n + l >= outLen) return -1; memcpy(out + n, rep, (size_t)l); n += l; s += skip; }
        else { if (n + 1 >= outLen) return -1; out[n++] = *s++; }
    }
    out[n] = 0;
    return n;
}

/* Pick and fill one line. Returns 1 and writes `out`, or 0 when nothing fits. */
static int botChatPick(int sit, int pers, int team, const botchat_ctx_t *ctx, char *out, int outLen, int lowerPct)
{
    static const botchat_ctx_t none = { 0, 0, 0, 0 };
    char area[32], name[32], enemy[32], buf[BOTCHAT_OUT];
    if (!botChat.loaded || sit < 0 || sit >= botChat.numSits || pers < 0 || pers >= BOTCHAT_PERS) return 0;
    if (team < 0 || team >= BOTCHAT_MAX_TEAMS) team = 0;
    if (!ctx) ctx = &none;
    botChatClean(ctx->area, area, sizeof(area), 1);
    botChatClean(ctx->name, name, sizeof(name), 0);
    botChatClean(ctx->enemy, enemy, sizeof(enemy), 0);
    if (strlen(name) > 12) { char *sp = strrchr(name, ' '); if (sp && sp[1]) memmove(name, sp + 1, strlen(sp + 1) + 1); name[12] = 0; }
    if (strlen(enemy) > 12) { char *sp = strrchr(enemy, ' '); if (sp && sp[1]) memmove(enemy, sp + 1, strlen(sp + 1) + 1); enemy[12] = 0; }
    unsigned have = (area[0] ? BOTCHAT_F_AREA : 0) | (ctx->count > 0 ? BOTCHAT_F_COUNT : 0) | (name[0] ? BOTCHAT_F_NAME : 0) | (enemy[0] ? BOTCHAT_F_ENEMY : 0);
    const botchat_sit_t *st = &botChat.sits[sit];
    /* one time in ten borrow another personality's voice, so the voices overlap a little */
    int usePers = pers;
    if (botChatRand() % 10 == 0) usePers = (int)(botChatRand() % BOTCHAT_PERS);
    if (!st->count[usePers]) usePers = pers;
    short *recent = botChat.recent[sit][team];
    for (int relax = 0; relax < 2; relax++) {                    /* second pass ignores the no-repeat window */
        int n = st->count[usePers], start = n ? (int)(botChatRand() % (unsigned)n) : 0;
        for (int k = 0; k < n; k++) {
            int li = st->first[usePers] + (start + k) % n, seen = 0;
            if (botChat.lineFlags[li] & ~have) continue;         /* needs a placeholder we can't fill */
            if (!relax) for (int r = 0; r < BOTCHAT_WINDOW; r++) if (recent[r] == li) seen = 1;
            if (seen) continue;
            if ((botChat.lineFlags[li] & BOTCHAT_F_AREA) && botChatAreaClash(botChat.line[li], area)) continue;
            int len = botChatFill(botChat.line[li], area, ctx->count, name, enemy, buf, sizeof(buf));
            if (len < 0 || len > BOTCHAT_MAX_TEXT || len >= outLen) continue;
            memmove(recent + 1, recent, sizeof(short) * (BOTCHAT_WINDOW - 1)); recent[0] = (short)li;
            /* typing style: some lines go out lower-case without the final full stop (25% by default, per bot via the roster) */
            if ((int)(botChatRand() % 100) < lowerPct) {
                const char *keep[3] = { area, name, enemy };
                for (int i = 0; buf[i]; i++) {
                    int protect = 0;
                    for (int w = 0; w < 3; w++) { size_t l = strlen(keep[w]); if (l && !strncmp(buf + i, keep[w], l)) { i += (int)l - 1; protect = 1; break; } }
                    if (!protect) buf[i] = (char)botChatLower((unsigned char)buf[i]);
                }
                if (len > 1 && buf[len - 1] == '.' && buf[len - 2] != '.') buf[--len] = 0;
            }
            memcpy(out, buf, (size_t)len + 1);
            return 1;
        }
        if (usePers != pers) { usePers = pers; relax = -1; }     /* borrowed voice had nothing: use our own */
    }
    return 0;
}

/* Ask for a line. Applies mode, chattiness, cooldowns and caps, then queues it with a typing delay. */
static int botChatSay(int now, int slot, int team, int pers, int sit, const botchat_ctx_t *ctx, int flags)
{
    if (!botChat.loaded || !botChat.mode || sit < 0 || sit >= botChat.numSits) return 0;
    if (slot < 0 || slot >= BOTCHAT_MAX_SLOTS || team < 0 || team >= BOTCHAT_MAX_TEAMS) return 0;
    const botchat_sit_t *st = &botChat.sits[sit];
    int force = flags & BOTCHAT_FORCE;
    if (st->channel == BOTCHAT_ALL && botChat.mode < 2) return 0;
    for (int i = 0; i < botChat.qn; i++) if (botChat.q[i].slot == slot) { botChat.dropped++; botChat.why[1]++; return 0; }   /* still typing */
    if (!force) {
        int chatty = botChat.voiceChatty[slot] >= 0 ? botChat.voiceChatty[slot] : botChatChatty[pers];
        /* information the team needs (contacts, objective events, what a dying bot saw) is not small talk:
         * even a quiet bot reports most of it */
        if (st->group == 0 || st->group == 3 || (flags & BOTCHAT_DEAD)) chatty = 75 + chatty / 4;
        if ((int)(botChatRand() % 100) >= chatty) { botChat.dropped++; botChat.why[2]++; return 0; }
        if (now >= botChat.botTimes[slot][2] && now - botChat.botTimes[slot][2] < 10000) { botChat.dropped++; botChat.why[3]++; return 0; }                    /* 3 per 10 s */
        for (int i = 0; i < 8; i++) if (botChat.botSitAt[slot][i][0] == sit + 1 && now < botChat.botSitAt[slot][i][1]) { botChat.dropped++; botChat.why[4]++; return 0; }
    }
    if (botChat.qn >= BOTCHAT_QUEUE) { botChat.dropped++; botChat.why[5]++; return 0; }
    botchat_q_t *q = &botChat.q[botChat.qn];
    if (!botChatPick(sit, pers, team, ctx, q->text, sizeof(q->text), botChat.voiceLower[slot])) { botChat.why[7]++; return 0; }
    int delay = (flags & BOTCHAT_NODELAY) ? 100 : 400 + (int)(botChatRand() % 800) + 12 * (int)strlen(q->text);
    q->dueAt = now + delay; q->slot = slot; q->team = team; q->sit = sit; q->channel = st->channel;
    botChat.qn++;
    if (st->cooldownMs) {
        int oldest = 0;
        for (int i = 1; i < 8; i++) if (botChat.botSitAt[slot][i][1] < botChat.botSitAt[slot][oldest][1]) oldest = i;
        botChat.botSitAt[slot][oldest][0] = sit + 1; botChat.botSitAt[slot][oldest][1] = now + st->cooldownMs;
    }
    botChat.lastSit[slot] = sit; botChat.lastAt[slot] = now;
    if (ctx && ctx->area) botChatClean(ctx->area, botChat.lastArea[slot], sizeof(botChat.lastArea[slot]), 1);
    return 1;
}

/* Per-bot voice from the roster: chattiness 0..100 (-1 keeps the personality default) and how often it types lower-case. */
static void botChatSetVoice(int slot, int chatty, int lowerPct)
{
    if (slot < 0 || slot >= BOTCHAT_MAX_SLOTS) return;
    botChat.voiceChatty[slot] = (signed char)(chatty > 100 ? 100 : chatty);
    botChat.voiceLower[slot] = (unsigned char)(lowerPct < 0 ? 25 : lowerPct > 100 ? 100 : lowerPct);
}

/* Drop a queued line (sit < 0: any) because it went stale before it was "typed". */
static void botChatCancel(int slot, int sit)
{
    for (int i = 0; i < botChat.qn; i++)
        if (botChat.q[i].slot == slot && (sit < 0 || botChat.q[i].sit == sit)) { botChat.q[i] = botChat.q[--botChat.qn]; i--; }
}

/* Emit queued lines that are due, oldest first, at most one per team every 1.5 s. Lines that wait more
 * than 2.5 s past their time are dropped: a late call-out is worse than none. */
static void botChatFrame(int now, botchat_emit_t emit)
{
    for (;;) {
        int best = -1;
        for (int i = 0; i < botChat.qn; i++) {
            botchat_q_t *q = &botChat.q[i];
            if (now - q->dueAt > 2500) { botChat.dropped++; botChat.why[6]++; *q = botChat.q[--botChat.qn]; i--; continue; }
            if (q->dueAt > now || now < botChat.teamNext[q->team]) continue;
            if (best < 0 || q->dueAt < botChat.q[best].dueAt) best = i;
        }
        if (best < 0) return;
        botchat_q_t q = botChat.q[best];
        botChat.q[best] = botChat.q[--botChat.qn];
        botChat.teamNext[q.team] = now + 1500;
        botChat.botTimes[q.slot][2] = botChat.botTimes[q.slot][1];
        botChat.botTimes[q.slot][1] = botChat.botTimes[q.slot][0];
        botChat.botTimes[q.slot][0] = now;
        botChat.said++;
        if (emit) emit(q.slot, q.team, q.channel, q.sit, q.text);
    }
}

/* Follow-up memory: what this bot last called, for fu_still_there and friends. */
static int botChatLastCall(int slot, int now, int withinMs, const char **area)
{
    if (slot < 0 || slot >= BOTCHAT_MAX_SLOTS || botChat.lastSit[slot] < 0 || now - botChat.lastAt[slot] > withinMs) return -1;
    if (area) *area = botChat.lastArea[slot];
    return botChat.lastSit[slot];
}

#endif /* TCP_BOT_CHAT_H */
