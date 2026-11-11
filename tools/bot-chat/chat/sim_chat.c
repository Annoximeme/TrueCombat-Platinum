/* sim_chat.c: plays out made-up rounds (bomb attack, bomb defence, capture the flag, team deathmatch) and prints the chat the bots would produce, using the real
 * picker and pacing in tcp_bot_chat.h. It is a reading tool: the fights are dice rolls, not the game.
 *
 * Build: cc -std=c99 -O1 sim_chat.c -o sim_chat
 * Run:   ./sim_chat phrases.txt roster.txt [seed] [rounds] [--events] [--mode N] [--game attack|defend|ctf|tdm|mix]
 *        --events also prints what happened (indented, starting with ">"), so the chat can be judged in context.
 */
#include "tcp_bot_chat.h"
#include "tcp_bot_listen.h"
#include <stdarg.h>

#define TEAM 1
#define NBOTS 5
#define HUMAN "RaziC"
typedef struct { char name[24]; int pers, chatty, lower; } rbot_t;
static rbot_t roster[64]; static int nroster;
static struct { int r, alive, area, hp, isCarrier, dealt; } bot[NBOTS];
static const char *const AREAS[] = { "Courtyard", "Warehouse", "Alley", "Bridge", "Market", "Tunnel", "Garage", "Tower", "Site A", "Site B" };
#define NAREAS 10
static const char *const ENEMIES[] = { "Kestrel", "^1Dutch", "mole", "[x] Varga", "Pim" };
static int respawns, score[2];
static int now, showEvents, linesOut, enemiesAlive, roundNo, ackSit[3], ackPending = -1; static char ackArea[32];
static unsigned rs;
static unsigned rnd(unsigned n) { rs = rs * 1103515245u + 12345u; return ((rs >> 10) & 0xfffff) % (n ? n : 1); }
static int S(const char *k) { int s = botChatSituation(k); if (s < 0) { printf("missing key %s\n", k); exit(2); } return s; }

static void stamp(void) { printf("[%d:%02d] ", now / 60000, (now / 1000) % 60); }
static void emit(int slot, int team, int channel, int sit, const char *text)
{
    (void)team; linesOut++;
    if (sit == ackSit[0] || sit == ackSit[1] || sit == ackSit[2]) ackPending = slot;      /* a contact call was shown: someone may answer it */
    stamp(); printf("%s(%s): %s\n", channel == BOTCHAT_ALL ? "[ALL] " : "", roster[bot[slot].r].name, text);
}
static void ev(const char *fmt, ...)
{
    if (!showEvents) return;
    va_list ap; va_start(ap, fmt); printf("        > "); vprintf(fmt, ap); printf("\n"); va_end(ap);
}
static void human(const char *text) { stamp(); printf("(%s): %s\n", HUMAN, text); }
static const char *N(int b);
static int say(int b, const char *key, const char *area, int count, const char *name, const char *enemy, int flags);
static int pickAlive(int not);
static void run(int ms)
{
    for (int end = now + ms; now < end; now += 100) {
        botChatFrame(now, emit);
        if (ackPending >= 0) {                                   /* one call in three gets an answer from a teammate */
            int from = ackPending, m = pickAlive(from); ackPending = -1;
            if (m >= 0 && rnd(3) == 0) say(m, "fu_ack_teammate_call", ackArea, 0, N(from), NULL, 0);
        }
    }
}
static const char *N(int b) { return roster[bot[b].r].name; }
static int say(int b, const char *key, const char *area, int count, const char *name, const char *enemy, int flags)
{
    botchat_ctx_t c = { area, count, name, enemy };
    int before[8]; memcpy(before, botChat.why, sizeof(before));
    int ok = botChatSay(now, b, TEAM, roster[bot[b].r].pers, S(key), &c, flags);
    static const char *const why[] = { "", "still typing the previous line", "chose to stay quiet", "said 3 lines in 10 s", "same call too recently", "queue full", "", "no line fits" };
    if (!ok && showEvents > 1) for (int i = 1; i < 8; i++) if (botChat.why[i] != before[i]) printf("        . %s says nothing for %s: %s\n", roster[bot[b].r].name, key, why[i]);
    return ok;
}
static int aliveCount(void) { int n = 0; for (int i = 0; i < NBOTS; i++) n += bot[i].alive; return n; }
static int pickAlive(int not) { int t[NBOTS], n = 0; for (int i = 0; i < NBOTS; i++) if (bot[i].alive && i != not) t[n++] = i; return n ? t[rnd((unsigned)n)] : -1; }
static int pickDead(void) { int t[NBOTS], n = 0; for (int i = 0; i < NBOTS; i++) if (!bot[i].alive) t[n++] = i; return n ? t[rnd((unsigned)n)] : -1; }

static void botDies(int b, const char *area, const char *how)
{
    bot[b].alive = 0; botChatCancel(b, -1);
    ev("%s is killed at %s (%s)", N(b), area, how);
    say(b, bot[b].dealt ? "dead_enemy_low" : how, area, respawns ? 0 : enemiesAlive, NULL, NULL, BOTCHAT_NODELAY | BOTCHAT_DEAD);
    int m = pickAlive(b);
    if (respawns) { score[1]++; if (m >= 0 && rnd(3) == 0) say(m, "teammate_down", area, 0, N(b), NULL, 0); return; }
    if (m >= 0 && aliveCount() > 1) say(m, "teammate_down", area, 0, N(b), NULL, 0);
    if (aliveCount() == 1) { int l = pickAlive(-1); ev("%s is the last one alive, %d enemies left", N(l), enemiesAlive); say(l, "clutch_start", NULL, enemiesAlive, NULL, NULL, BOTCHAT_FORCE); }
}

static void fight(int b, const char *area, int n)
{
    static const char *const kills[] = { "kill_confirm", "kill_confirm", "kill_confirm", "kill_confirm", "kill_headshot", "kill_headshot", "kill_long", "kill_unaware" };
    static const char *const deaths[] = { "dead_info", "dead_info", "died_in_duel", "died_from_behind", "died_to_sniper", "died_reloading", "died_to_grenade" };
    int clutch = aliveCount() == 1, got = 0;
    for (int k = 0; k < n && bot[b].alive && enemiesAlive > 0; k++) {
        run(600 + (int)rnd(1800));
        int roll = (int)rnd(100), pers = roster[bot[b].r].pers;
        int win = 52 + (pers == BOTCHAT_MARKSMAN ? 8 : 0) - (pers == BOTCHAT_ENTRY ? 4 : 0);
        if (roll < win) {
            const char *en = ENEMIES[rnd(5)];
            if (respawns) { score[0]++; bot[b].dealt++; ev("%s kills %s at %s", N(b), en, area);
                say(b, got++ > 0 ? "kill_multi" : bot[b].dealt == 4 ? "on_fire" : kills[rnd(8)], area, 0, NULL, en, 0); continue; }
            enemiesAlive--;
            const char *kk = kills[rnd(8)]; if (bot[b].hp < 30) kk = "kill_low_hp";
            if (got++ > 0) kk = "kill_multi";
            ev("%s kills %s at %s, %d enemies left", N(b), en, area, enemiesAlive);
            if (enemiesAlive == 0) say(b, "kill_last", NULL, 0, NULL, NULL, 0);
            else say(b, kk, area, 0, NULL, en, 0);
            if (!clutch && enemiesAlive == 1) { run(1500); int m = pickAlive(b); if (m >= 0) say(m, "last_enemy", NULL, 0, NULL, NULL, 0); }
            else if (!clutch && enemiesAlive > 1 && rnd(3) == 0) { run(1200); int m = pickAlive(-1); if (m >= 0) say(m, "enemies_left", NULL, enemiesAlive, NULL, NULL, 0); }
        } else if (roll < win + 18) {
            bot[b].hp -= 30 + (int)rnd(40);
            if (bot[b].hp <= 0) { if (respawns) bot[b].dealt = 0; botDies(b, area, deaths[rnd(7)]); return; }
            ev("%s is hit (%d hp)", N(b), bot[b].hp);
            say(b, bot[b].hp < 30 ? "damage_low" : "damage_taken", area, 0, NULL, NULL, 0);
            if (rnd(2)) { run(900); say(b, "falling_back", NULL, 0, NULL, NULL, 0); ev("%s backs off", N(b)); return; }
        } else if (roll < win + 30) {
            ev("%s loses sight of the enemy at %s", N(b), area);
            say(b, "contact_lost", area, 0, NULL, NULL, 0);
            run(2500 + (int)rnd(2500));
            if (rnd(2)) { ev("%s sees him again at %s", N(b), area); say(b, "fu_found_again", area, 0, NULL, NULL, 0); }
        } else { if (!respawns) bot[b].dealt = rnd(4) == 0; else bot[b].dealt = 0; botDies(b, area, deaths[rnd(7)]); return; }
    }
}

static void contact(const char *area)
{
    int b = pickAlive(-1); if (b < 0 || enemiesAlive <= 0) return;
    int n = 1 + (int)rnd((unsigned)(enemiesAlive > 3 ? 3 : enemiesAlive));
    if (respawns) n = 1 + (int)rnd(2);
    ev("%s sees %d enem%s at %s", N(b), n, n == 1 ? "y" : "ies", area);
    snprintf(ackArea, sizeof(ackArea), "%s", area);
    static const char *const ones[] = { "contact_one", "contact_one", "contact_one", "contact_sniper", "contact_unaware", "contact_running", "contact_static", "contact_sneaking" };
    if (n == 1) say(b, ones[rnd(8)], area, 0, NULL, NULL, 0);
    else say(b, rnd(4) == 0 ? "enemy_pushing" : "contact_many", area, n, NULL, NULL, 0);
    run(900);
    int m = pickAlive(b);
    if (m >= 0 && roster[bot[m].r].pers == BOTCHAT_SUPPORT && rnd(2)) { int fl = (int)rnd(2); run(700); ev("%s throws a %s", N(m), fl ? "flash" : "smoke"); say(m, fl ? "throw_flash" : "throw_smoke", area, 0, NULL, NULL, 0); }
    const char *la = NULL;
    fight(b, area, n);
    if (bot[b].alive && enemiesAlive > 0 && rnd(3) == 0 && botChatLastCall(b, now, 20000, &la) >= 0) {
        run(3000); ev("%s still sees one at %s", N(b), area); say(b, "fu_still_there", area, 0, NULL, NULL, 0);
    }
    if (m >= 0 && bot[m].alive && enemiesAlive > 0 && rnd(2)) { ev("%s joins the fight at %s", N(m), area); fight(m, area, 1); }
}

static void setupTeam(void)
{
    int used[64] = { 0 }, perTaken[BOTCHAT_PERS] = { 0 };
    for (int i = 0; i < NBOTS; i++) {                       /* one of each personality first, like the roster suggests */
        int r; do r = (int)rnd((unsigned)nroster); while (used[r] || perTaken[roster[r].pers]);
        used[r] = 1; perTaken[roster[r].pers] = 1;
        bot[i].r = r; bot[i].alive = 1; bot[i].hp = 100; bot[i].isCarrier = 0; bot[i].dealt = 0;
        botChatSetVoice(i, roster[r].chatty, roster[r].lower);
    }
    enemiesAlive = 5; now = 0; respawns = 0; score[0] = score[1] = 0; botChatRoundReset();
}
static void header(const char *what)
{
    printf("\n=== Round %d: %s. Team: ", ++roundNo, what);
    for (int i = 0; i < NBOTS; i++) printf("%s (%s)%s", N(i), botChatPersNames[roster[bot[i].r].pers], i < NBOTS - 1 ? ", " : "");
    printf(" + %s (human) ===\n", HUMAN);
}

/* The human types something. It goes through the real parser (tcp_bot_listen.h) and the bots it reaches answer. */
static void humanTypes(const char *fmt, ...)
{
    char text[96]; va_list ap; va_start(ap, fmt); vsnprintf(text, sizeof(text), fmt, ap); va_end(ap);
    const char *names[NBOTS]; for (int i = 0; i < NBOTS; i++) names[i] = N(i);
    botlisten_t r; human(text);
    if (!botListenParse(text, names, NBOTS, AREAS, NAREAS, &r)) { ev("the bots do not understand that"); return; }
    ev("understood as: %s%s%s%s", botListenNames[r.intent], r.area >= 0 ? ", area " : "", r.area >= 0 ? AREAS[r.area] : "", r.addressed == BOTLISTEN_NAMED ? ", for one bot" : r.addressed == BOTLISTEN_GROUP ? ", for the team" : ", nobody addressed");
    const char *area = r.area >= 0 ? AREAS[r.area] : NULL;
    int first = r.addressed == BOTLISTEN_NAMED ? r.target : pickAlive(-1);
    if (first < 0) return;
    if (!bot[first].alive) { say(first, respawns ? "order_busy" : "order_dead", area, 0, HUMAN, NULL, BOTCHAT_FORCE | BOTCHAT_DEAD); return; }
    int can = rnd(6) != 0;
    say(first, botListenReplyKey(r.intent, can), area, respawns ? 0 : enemiesAlive, HUMAN, NULL, BOTCHAT_FORCE);
    if (r.addressed == BOTLISTEN_GROUP && BL_ORDER(r.intent)) { int c = pickAlive(first); if (c >= 0) { run(400); say(c, botListenReplyKey(r.intent, 1), area, 0, HUMAN, NULL, BOTCHAT_FORCE); } }
}
static void roundEnd(int won, const char *note, const char *wonKey, const char *lostKey)
{
    int clutch = aliveCount() == 1 && !respawns;
    printf("        --- round %s (%s) ---\n", won ? "WON" : "LOST", note);
    now += 1500;
    if (clutch && won) { int l = pickAlive(-1); say(l, "clutch_won", NULL, 0, NULL, NULL, 0); }
    for (int i = 0, said = 0; i < NBOTS && said < 2; i++) {
        int b = (int)rnd(NBOTS);
        said += say(b, won ? wonKey : lostKey, NULL, 0, NULL, NULL, bot[b].alive ? 0 : BOTCHAT_DEAD);
    }
    run(7000);
}

static void playAttack(void)
{
    setupTeam();
    const char *site = AREAS[8 + rnd(2)], *a1 = AREAS[rnd(8)], *a2 = AREAS[rnd(8)];
    { char h[48]; snprintf(h, sizeof(h), "bomb, attacking %s", site); header(h); }
    int carrier = (int)rnd(NBOTS); bot[carrier].isCarrier = 1;
    for (int i = 0; i < NBOTS; i++) if (rnd(2)) say(i, i == carrier ? "bomb_site_choice" : "round_plan_attack", i == carrier ? site : (rnd(2) ? site : a1), 0, NULL, NULL, 0);
    run(9000);
    if (rnd(2)) { int b = pickAlive(-1); say(b, rnd(2) ? "going_quiet" : "moving_to", a1, 0, NULL, NULL, 0); }
    run(8000 + (int)rnd(8000));
    if (rnd(3) == 0) { int b = pickAlive(-1); ev("%s hears footsteps at %s", N(b), a2); say(b, "enemy_heard", a2, 0, NULL, NULL, 0); run(4000); }
    contact(a1);
    run(3000 + (int)rnd(4000));
    if (aliveCount() >= 2 && enemiesAlive > 0) {            /* the human gives an order and pings */
        int b;
        switch (rnd(6)) {
        case 0: humanTypes("bots push %s", site + 5); break;
        case 1: humanTypes("bots hold here"); break;
        case 2: humanTypes("%s smoke %s pls", N(pickAlive(-1)), a2); break;
        case 3: humanTypes("%s follow me", N(pickAlive(-1))); break;
        case 4: humanTypes("how many left?"); break;
        default: humanTypes("team dont push yet"); break;
        }
        run(5000);
        if (rnd(2)) { stamp(); printf("%s pings: enemy at %s\n", HUMAN, a2); b = pickAlive(-1); say(b, "ping_enemy_ack", a2, 0, HUMAN, NULL, BOTCHAT_FORCE); run(3000); }
    }
    if (aliveCount() && enemiesAlive > 0) contact(a2);
    run(3000 + (int)rnd(5000));
    int planted = 0;
    if (aliveCount() && enemiesAlive > 0) {
        int p = bot[carrier].alive ? carrier : pickAlive(-1);
        if (!bot[carrier].alive) { ev("%s picks up the bomb", N(p)); say(p, "bomb_pickup", NULL, 0, NULL, NULL, 0); run(4000); }
        ev("%s reaches %s and plants", N(p), site);
        say(p, "bomb_planting", site, 0, NULL, NULL, BOTCHAT_FORCE); run(5000);
        planted = 1; int m = pickAlive(p); say(m >= 0 ? m : p, "bomb_planted", site, 0, NULL, NULL, 0);
        run(3500); m = pickAlive(-1); say(m, rnd(2) ? "post_plant_pos" : "play_time", a2, 0, NULL, NULL, 0);
        run(6000 + (int)rnd(6000));
        if (enemiesAlive > 0 && aliveCount()) {
            int b = pickAlive(-1); ev("%s sees an enemy on the bomb", N(b)); say(b, "enemy_defusing", NULL, 0, NULL, NULL, BOTCHAT_NODELAY);
            run(1500);
            if (rnd(100) < 60) { enemiesAlive--; ev("%s kills the defuser, %d enemies left", N(b), enemiesAlive); say(b, "kill_defuser", NULL, 0, NULL, NULL, 0); }
            else botDies(b, site, "dead_info");
        }
    }
    while (aliveCount() && enemiesAlive > 0 && !planted) { run(4000 + (int)rnd(5000)); contact(AREAS[rnd(NAREAS)]); }
    if (planted && aliveCount() && enemiesAlive > 0 && rnd(2)) { run(5000); contact(site); }
    run(4000);
    int won = aliveCount() > 0 && (enemiesAlive == 0 || planted);
    int clutch = aliveCount() == 1;
    printf("        --- round %s (%d of 5 bots alive, %d enemies left%s) ---\n", won ? "WON" : "LOST", aliveCount(), enemiesAlive, planted ? ", bomb planted" : "");
    now += 1500;
    if (clutch && won) { int l = pickAlive(-1); say(l, "clutch_won", NULL, 0, NULL, NULL, 0); }
    for (int i = 0, said = 0; i < NBOTS && said < 2; i++) {
        int b = (int)rnd(NBOTS);
        const char *k = won ? (planted && rnd(2) ? (rnd(2) ? "round_won_detonated" : "round_won_bomb") : aliveCount() == NBOTS ? "flawless_round" : clutch ? "close_round_won" : "round_won") : "round_lost";
        said += say(b, k, NULL, 0, NULL, NULL, bot[b].alive ? 0 : BOTCHAT_DEAD);
    }
    run(7000);
    (void)pickDead;
}

static void playDefend(void)
{
    setupTeam();
    const char *site = AREAS[8 + rnd(2)], *other = site == AREAS[8] ? AREAS[9] : AREAS[8], *a1 = AREAS[rnd(8)], *a2 = AREAS[rnd(8)];
    header("bomb, defending both sites");
    for (int i = 0; i < NBOTS; i++) if (rnd(2)) say(i, "round_plan_defend", i < 2 ? AREAS[8] : i < 4 ? AREAS[9] : a1, 0, NULL, NULL, 0);
    run(10000);
    { int b = pickAlive(-1); say(b, "holding", b < 2 ? AREAS[8] : b < 4 ? AREAS[9] : a1, 0, NULL, NULL, 0); }
    run(9000 + (int)rnd(6000));
    if (rnd(2)) { int b = pickAlive(-1); ev("%s has seen nobody at %s for 20 s", N(b), other); say(b, "nobody_coming", other, 0, NULL, NULL, 0); run(3000); }
    if (rnd(3) == 0) { int b = pickAlive(-1); ev("%s hears footsteps at %s", N(b), a1); say(b, "enemy_heard", a1, 0, NULL, NULL, 0); run(3000); }
    contact(a1);
    run(2500 + (int)rnd(3000));
    if (aliveCount() && enemiesAlive > 0) {
        int b = pickAlive(-1);
        if (rnd(2)) { ev("%s sees the bomb carrier at %s", N(b), a2); say(b, "enemy_bomb_carrier", a2, 0, NULL, NULL, 0); }
        else { ev("%s sees enemies leaving towards %s", N(b), site); say(b, "enemy_rotating", site, 0, NULL, NULL, 0); }
        run(1800); int m = pickAlive(b);
        if (m >= 0) { ev("%s decides the team should rotate to %s", N(m), site); say(m, "rotate_call", site, 0, NULL, NULL, 0); run(1200); }
        m = pickAlive(b); if (m >= 0 && rnd(2)) { say(m, "rotating_self", site, 0, NULL, NULL, 0); }
        run(3000);
    }
    if (aliveCount() >= 2 && enemiesAlive > 0) {
        switch (rnd(5)) {
        case 0: humanTypes("%s watch %s", N(pickAlive(-1)), a2); break;
        case 1: humanTypes("everyone to %s", site); break;
        case 2: humanTypes("where are they"); break;
        case 3: humanTypes("%s stay %s", N(pickAlive(-1)), other); break;
        default: humanTypes("guys fall back"); break;
        }
        run(4000);
    }
    if (aliveCount() && enemiesAlive > 0) contact(site);
    run(3000);
    int planted = 0, defused = 0;
    if (aliveCount() && enemiesAlive > 1 && rnd(100) < 55) {
        int b = pickAlive(-1);
        if (rnd(2)) { ev("%s sees an enemy planting at %s", N(b), site); say(b, "enemy_planting", site, 0, NULL, NULL, BOTCHAT_NODELAY); }
        else { ev("%s hears the plant", N(b)); say(b, "heard_plant", NULL, 0, NULL, NULL, 0); }
        run(4000); planted = 1;
        ev("bomb is planted at %s", site);
        b = pickAlive(-1); say(b, "enemy_bomb_planted", site, 0, NULL, NULL, BOTCHAT_FORCE);
        run(2500);
        if (aliveCount() >= 2) { b = pickAlive(-1); say(b, "retake_start", site, 0, NULL, NULL, 0); run(3500); }
        if (aliveCount() && rnd(5) == 0) { run(9000); b = pickAlive(-1); ev("%s works out that nobody can reach and defuse the bomb in time", N(b)); say(b, "save_call", NULL, 0, NULL, NULL, 0); run(5000); }
        else {
            contact(site);
            run(2000);
            if (aliveCount()) {
                int d = pickAlive(-1), m = pickAlive(d);
                if (enemiesAlive == 0) { ev("site is clear"); say(d, "retake_done", site, 0, NULL, NULL, 0); run(1500); }
                else if (rnd(2)) { ev("%s says the timer is getting short", N(d)); say(d, "bomb_ticking", NULL, 0, NULL, NULL, 0); run(1500); }
                ev("%s starts defusing", N(d)); say(d, "bomb_defusing", NULL, 0, NULL, NULL, BOTCHAT_FORCE);
                if (m >= 0 && enemiesAlive > 0) { run(900); say(d, "need_defuser_cover", NULL, 0, NULL, NULL, 0); }
                run(5000);
                if (enemiesAlive > 0 && rnd(100) < 35) botDies(d, site, "dead_info"); else defused = 1;
            }
        }
    }
    for (int told = 0; !planted && aliveCount() && enemiesAlive > 0 && now < 110000; ) {
        run(4000 + (int)rnd(5000));
        if (!told && now > 80000) { told = 1; int b = pickAlive(-1); ev("30 seconds left, no bomb planted"); say(b, rnd(2) ? "time_hold" : "time_30", NULL, 0, NULL, NULL, 0); run(3000); }
        contact(AREAS[rnd(NAREAS)]);
    }
    run(3000);
    int timeout = !planted && enemiesAlive > 0 && aliveCount() > 0;
    int won = defused || (!planted && aliveCount() > 0);
    char note[96]; snprintf(note, sizeof(note), "%d of 5 bots alive, %d enemies left%s", aliveCount(), enemiesAlive, defused ? ", bomb defused" : planted ? ", bomb went off" : timeout ? ", time ran out" : "");
    roundEnd(won, note, defused ? "round_won_defused" : timeout ? "round_won_time" : aliveCount() == NBOTS ? "flawless_round" : "round_won", "round_lost");
}

/* Respawn modes: dead bots come back after a few seconds. */
static void reviveAll(void)
{
    for (int i = 0; i < NBOTS; i++) if (!bot[i].alive) { bot[i].alive = 1; bot[i].hp = 100; if (rnd(4) == 0) { ev("%s is back in", N(i)); say(i, "respawned", NULL, 0, NULL, NULL, 0); } }
    for (int i = 0; i < NBOTS; i++) if (bot[i].hp < 100 && rnd(2)) bot[i].hp = 100;
}

static void playCTF(void)
{
    setupTeam(); respawns = 1;
    header("capture the flag, 4 minutes shown");
    int caps[2] = { 0, 0 };
    for (int i = 0; i < NBOTS; i++) if (rnd(3) == 0) say(i, i == 0 ? "flag_going" : i == 1 ? "flag_defend" : "map_start", NULL, 0, NULL, NULL, 0);
    run(8000);
    for (int phase = 0; phase < 4; phase++) {
        const char *a1 = AREAS[rnd(8)], *a2 = AREAS[rnd(8)];
        reviveAll();
        if (rnd(2)) { int b = pickAlive(-1); say(b, rnd(2) ? "flag_going" : "moving_to", a1, 0, NULL, NULL, 0); }
        run(6000 + (int)rnd(5000));
        contact(a1); reviveAll();
        run(3000 + (int)rnd(3000));
        if (rnd(100) < 60) {                                  /* we take their flag */
            int c = pickAlive(-1), m = pickAlive(c);
            ev("%s picks up the enemy flag", N(c)); say(c, "flag_taken", NULL, 0, NULL, NULL, BOTCHAT_FORCE);
            run(1500); if (m >= 0) { ev("%s moves to escort %s", N(m), N(c)); say(m, "flag_carrier_escort", NULL, 0, N(c), NULL, 0); }
            run(5000);
            if (rnd(3) == 0) humanTypes("%s cover me", N(pickAlive(c)));
            fight(c, a2, 1);
            if (bot[c].alive && rnd(100) < 70) { caps[0]++; ev("%s captures the flag, %d-%d", N(c), caps[0], caps[1]); say(c, "flag_captured", NULL, 0, NULL, NULL, BOTCHAT_FORCE);
                run(1200); if (caps[0] == caps[1] + 1) { int o = pickAlive(c); if (o >= 0) say(o, "lead_taken", NULL, 0, NULL, NULL, 0); } }
            else { if (bot[c].alive) botDies(c, a2, "dead_info"); int o = pickAlive(c); ev("the flag is dropped at %s", a2); if (o >= 0) say(o, "flag_dropped", a2, 0, NULL, NULL, 0);
                run(3500); o = pickAlive(c); if (o >= 0 && rnd(2)) { ev("the enemy returns their flag"); say(o, "flag_enemy_returned", NULL, 0, NULL, NULL, 0); } else if (o >= 0) { ev("%s picks the flag up again", N(o)); say(o, "flag_taken", NULL, 0, NULL, NULL, 0); run(4000);
                    if (rnd(3) == 0) { ev("the enemy takes our flag too: nobody can capture"); say(pickAlive(-1), "flag_standoff", NULL, 0, NULL, NULL, 0); run(5000); ev("%s kills their carrier at %s", N(pickAlive(o)), a1); say(pickAlive(o), "kill_flag_carrier", a1, 0, NULL, NULL, 0); run(3000); }
                    caps[0]++; ev("%s captures the flag, %d-%d", N(o), caps[0], caps[1]); say(o, "flag_captured", NULL, 0, NULL, NULL, BOTCHAT_FORCE); } }
        } else {                                              /* they take ours */
            int b = pickAlive(-1);
            ev("the enemy takes our flag"); say(b, "flag_lost", NULL, 0, NULL, NULL, BOTCHAT_FORCE);
            run(2500); b = pickAlive(-1); ev("%s sees their carrier at %s", N(b), a2); say(b, "enemy_flag_carrier", a2, 0, NULL, NULL, 0);
            if (rnd(3) == 0) { run(800); humanTypes("bots %s", a2); }
            run(2500);
            if (rnd(100) < 55) { score[0]++; ev("%s kills the carrier at %s", N(b), a2); say(b, "kill_flag_carrier", a2, 0, NULL, NULL, 0); run(2500); int o = pickAlive(-1); ev("%s returns the flag", N(o)); say(o, "flag_returned", NULL, 0, NULL, NULL, 0); }
            else { caps[1]++; ev("the enemy captures, %d-%d", caps[0], caps[1]); say(pickAlive(-1), "flag_enemy_captured", NULL, 0, NULL, NULL, 0); if (caps[1] == caps[0] + 1 && caps[1] > 1) { run(1500); say(pickAlive(-1), "lead_lost", NULL, 0, NULL, NULL, 0); } else if (caps[0] == caps[1]) { run(1500); say(pickAlive(-1), "score_tied", NULL, 0, NULL, NULL, 0); } }
        }
        run(5000 + (int)rnd(5000));
        if (phase == 2) { ev("one minute left"); say(pickAlive(-1), "time_60", NULL, 0, NULL, NULL, 0); }
    }
    char note[64]; snprintf(note, sizeof(note), "flags %d-%d", caps[0], caps[1]);
    reviveAll();
    if (caps[0] == caps[1]) { printf("        --- match DRAWN (%s) ---\n", note); now += 1500; say((int)rnd(NBOTS), "close_match_end", NULL, 0, NULL, NULL, 0); run(6000); }
    else roundEnd(caps[0] > caps[1], note, "match_won", "match_lost");
}

static void playTDM(void)
{
    setupTeam(); respawns = 1;
    header("team deathmatch, 3 minutes shown");
    for (int i = 0; i < NBOTS; i++) if (rnd(4) == 0) say(i, "map_start", NULL, 0, NULL, NULL, 0);
    run(6000);
    int lead = 0, deathsRow[NBOTS] = { 0 }; const char *nemesis = ENEMIES[rnd(5)];
    for (int phase = 0; phase < 6; phase++) {
        int before[NBOTS]; for (int i = 0; i < NBOTS; i++) before[i] = bot[i].alive;
        reviveAll();
        run(4000 + (int)rnd(5000));
        contact(AREAS[rnd(8)]);
        for (int i = 0; i < NBOTS; i++) {
            if (!bot[i].alive) { if (++deathsRow[i] == 3) { run(2500); ev("%s was killed by %s three times in a row", N(i), nemesis); say(i, "dominated_by", NULL, 0, NULL, nemesis, BOTCHAT_DEAD); } }
            else if (deathsRow[i] >= 2 && bot[i].dealt) { ev("%s gets %s back", N(i), nemesis); say(i, "revenge", NULL, 0, NULL, nemesis, 0); deathsRow[i] = 0; }
            else if (bot[i].dealt) deathsRow[i] = 0;
        }
        (void)before;
        run(3000 + (int)rnd(3000));
        int l = score[0] > score[1] ? 1 : score[0] < score[1] ? -1 : 0;
        if (l != lead && l != 0) { int b = pickAlive(-1); if (b >= 0) { ev("score is %d-%d", score[0], score[1]); if (l > 0 || lead > 0) say(b, l > 0 ? "lead_taken" : "lead_lost", NULL, 0, NULL, NULL, 0); } }
        if (l) lead = l;
        if (phase == 1 && rnd(2)) { int b = pickDead(); if (b >= 0) { reviveAll(); ev("%s is killed right after spawning", N(b)); bot[b].alive = 0; say(b, "spawn_killed", NULL, 0, NULL, NULL, BOTCHAT_DEAD); } }
        if (phase == 2) switch (rnd(4)) { case 0: humanTypes("gj %s", N(pickAlive(-1))); break; case 1: humanTypes("are you bots?"); break; case 2: humanTypes("team regroup"); break; default: humanTypes("lol"); break; }
        if (phase == 5 && score[0] > score[1]) { int b = pickAlive(-1); ev("the team needs 3 more kills to win"); if (b >= 0) say(b, "kills_to_win", NULL, 3, NULL, NULL, 0); }
        if (phase == 4) { run(2000); ev("one minute left, %d-%d", score[0], score[1]); int b = pickAlive(-1); if (b >= 0) say(b, "time_60", NULL, 0, NULL, NULL, 0); }
    }
    reviveAll();
    char note[64]; snprintf(note, sizeof(note), "kills %d-%d", score[0], score[1]);
    int d = score[0] - score[1];
    if (d == 0) { printf("        --- match DRAWN (%s) ---\n", note); now += 1500; say((int)rnd(NBOTS), "close_match_end", NULL, 0, NULL, NULL, 0); run(6000); }
    else roundEnd(d > 0, note, d <= 2 && d >= -2 ? "close_match_end" : "match_won", d >= -2 ? "close_match_end" : "match_lost");
    humanTypes("gg"); run(4000);
}

int main(int argc, char **argv)
{
    if (argc < 3) { printf("usage: sim_chat phrases.txt roster.txt [seed] [rounds] [--events] [--mode N] [--game attack|defend|ctf|tdm|mix]\n"); return 2; }
    int rounds = 3; unsigned seed = 1; int mode = 2, pos = 0, game = 0;
    for (int i = 3; i < argc; i++) {
        if (!strcmp(argv[i], "--events")) showEvents = 1;
        else if (!strcmp(argv[i], "--why")) showEvents = 2;
        else if (!strcmp(argv[i], "--mode") && i + 1 < argc) mode = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--game") && i + 1 < argc) { const char *g = argv[++i]; game = !strcmp(g, "defend") ? 1 : !strcmp(g, "ctf") ? 2 : !strcmp(g, "tdm") ? 3 : !strcmp(g, "mix") ? 4 : 0; }
        else if (pos++ == 0) seed = (unsigned)atoi(argv[i]); else rounds = atoi(argv[i]);
    }
    FILE *f = fopen(argv[1], "rb"); if (!f) { printf("can't open %s\n", argv[1]); return 2; }
    fseek(f, 0, SEEK_END); long len = ftell(f); fseek(f, 0, SEEK_SET);
    char *text = malloc((size_t)len); if (fread(text, 1, (size_t)len, f) != (size_t)len) return 2; fclose(f);
    int n = botChatLoad(text, (int)len); free(text);
    ackSit[0] = botChatSituation("contact_one"); ackSit[1] = botChatSituation("contact_many"); ackSit[2] = botChatSituation("enemy_pushing");
    if (n <= 0) { printf("bank failed to load (%d)\n", n); return 2; }
    f = fopen(argv[2], "r"); if (!f) { printf("can't open %s\n", argv[2]); return 2; }
    char row[256];
    while (fgets(row, sizeof(row), f) && nroster < 64) {
        char name[24], pers[16]; int v[10];
        if (row[0] == '#' || sscanf(row, "%23s %15s %d %d %d %*s %d %d %d %d %d %d", name, pers, &v[0], &v[1], &v[2], &v[3], &v[4], &v[5], &v[6], &v[7], &v[8]) < 11) continue;
        rbot_t *r = &roster[nroster]; snprintf(r->name, sizeof(r->name), "%s", name);
        r->pers = botChatPersonality(pers); r->chatty = v[7]; r->lower = v[8];
        if (r->pers >= 0) nroster++;
    }
    fclose(f);
    if (nroster < NBOTS) { printf("roster too small (%d)\n", nroster); return 2; }
    rs = seed * 2654435761u + 7; botChat.seed = seed * 40503u + 11; botChat.mode = mode;
    printf("Chat simulation, seed %u, %d rounds, bank of %d lines, %d bots in the roster. Fights are dice rolls; area and player names are made up.\n", seed, rounds, n, nroster);
    int total = 0, time = 0;
    for (int r = 0; r < rounds; r++) {
        int g = game == 4 ? r % 4 : game;
        if (g == 0) playAttack(); else if (g == 1) playDefend(); else if (g == 2) playCTF(); else playTDM();
        total = linesOut; time += now;
    }
    printf("\n%d bot lines in %d rounds (%.1f per round, one every %.0f s on average). %d requests held back: %d still typing, %d stayed quiet, %d bot cap, %d cooldown, %d stale, %d no fitting line.\n",
           total, rounds, (double)total / rounds, total ? time / 1000.0 / total : 0.0, botChat.dropped, botChat.why[1], botChat.why[2], botChat.why[3], botChat.why[4], botChat.why[6], botChat.why[7]);
    return 0;
}
