#!/usr/bin/env python3
"""Builds voice_map.txt: which radio voice line fits which chat situation.

  python voice_build.py <phrases.txt> <outdir>

A "concept" is what the radio line means (enemy_spotted, cover_me ...). The real sound ids differ per game build,
so the map stops at concepts; voice_check.py ties each concept to a real line from the game's .voice files."""
import re, sys

# concept -> words that identify it in a .voice file (id or caption). Used by voice_check.py.
CONCEPTS = {
    "affirmative":   r"affirmative|roger|copy that|^yes\b|yes sir",
    "negative":      r"negative|^no\b|no way|can't do",
    "enemy_spotted": r"enemy spotted|enemy sighted|contact|hostile|tango",
    "sniper":        r"enemy sniper|sniper spotted|sniper!",
    "need_backup":   r"back ?up|need help|reinforcement|assist",
    "cover_me":      r"cover me|covering fire",
    "follow_me":     r"follow me|on me",
    "hold_position": r"hold (this |your |the )?position|hold here|hold up|stay put|defend",
    "go":            r"go go|move out|move it|let's go|lets go|attack|storm",
    "fall_back":     r"fall ?back|retreat|pull back|get out",
    "regroup":       r"regroup|stick together|group up",
    "fire_in_hole":  r"fire in the hole|grenade|frag out",
    "taking_fire":   r"taking fire|under fire|i'?m hit|pinned",
    "area_clear":    r"all clear|area clear|^clear$|secure",
    "enemy_down":    r"enemy down|got him|got one|target down|tango down|hostile down",
    "man_down":      r"man down|lost one|teammate down",
    "in_position":   r"in position|i'?m set|ready",
    "on_my_way":     r"on my way|^moving|^coming",
    "bomb_planted":  r"bomb (has been |is )?planted|charge (is )?set",
    "defusing":      r"defus",
    "objective":     r"objective|flag|bomb",
    "thanks":        r"thank",
    "sorry":         r"sorry|oops|my bad",
    "cheer":         r"^cheer$|alright|yeah|hooray|well done|good (job|work)",
    "greeting":      r"^hi\b|hello|hey",
    "goodbye":       r"bye|see you|later",
    "good_game":     r"good game|gg",
    "quiet":         r"quiet|silence|shh",
    "spread_out":    r"spread|split",
    "wait":          r"wait|hold on|not yet",
    "flank":         r"flank|go around",
}

# situation -> concept. First matching rule wins; situations with no rule get text only.
RULES = [
    (r"^contact_sniper$|^kill_sniper$", None), (r"^contact_sniper$", "sniper"),
    (r"^contact_lost$|^contact_far$", None),
    (r"^contact_|^enemy_(behind|above|below|prone|camping|pushing|lone|jiggling|on_ladder|in_water|in_spawn|bomb_carrier|flag_carrier|rotating)$|^ping_enemy_ack$", "enemy_spotted"),
    (r"^kill_(confirm|headshot|long|unaware|pistol|knife|wallbang|through_smoke|low_hp|flanker|carrier|flag_carrier|defuser|last)$", "enemy_down"),
    (r"^teammate_down$", "man_down"),
    (r"^need_help$|^need_defuser_cover$|^carrier_needs_escort$|^numbers_disadvantage$", "need_backup"),
    (r"^damage_taken$|^damage_low$|^suppressed$", "taking_fire"),
    (r"^throw_frag$|^grenade_incoming$|^enemy_grenade_seen$", "fire_in_hole"),
    (r"^area_clear$|^retake_done$|^bomb_site_empty$|^nobody_coming$", "area_clear"),
    (r"^holding$|^fu_still_holding$|^bomb_guard$|^flag_defend$|^covering$|^watching_back$|^post_plant_pos$", "in_position"),
    (r"^moving_to$|^rotating_self$|^arriving$|^fu_answer_need_help$|^flag_going$|^order_goto$|^order_regroup$|^ping_go_here_ack$|^ping_help_ack$", "on_my_way"),
    (r"^falling_back$|^save_call$|^order_fallback$", "fall_back"),
    (r"^execute_go$|^entry_going$|^time_low$|^retake_start$|^rotate_call$", "go"),
    (r"^execute_wait$|^order_wait$", "wait"),
    (r"^stay_together$", "regroup"), (r"^spread_out$|^order_spread$", "spread_out"),
    (r"^going_quiet$|^quiet_round$|^order_quiet$", "quiet"),
    (r"^flanking$|^order_flank$", "flank"),
    (r"^bomb_planted$", "bomb_planted"), (r"^bomb_defusing$", "defusing"),
    (r"^squad_leader$|^flag_taken$", "follow_me"),
    (r"^order_(follow|hold|push|cover_me|watch|smoke|flash|frag|drop_bomb|take_bomb|plant|defuse|lead|stack)$|^ping_(watch|danger|bomb)_ack$|^fu_ack_teammate_call$", "affirmative"),
    (r"^order_(busy|too_far|no_utility|declined_role|dead)$|^fu_cant_help$|^ask_unknown_reply$", "negative"),
    (r"^reply_thanks$", None), (r"^fu_thanks_teammate$|^human_call_thanks$|^saved_by_teammate$", "thanks"),
    (r"^in_the_way_sorry$|^friendly_fire_did$|^teamkilled_someone$|^nade_own_team$|^reply_blame$", "sorry"),
    (r"^nice_shot_teammate$|^human_(first_blood|multi_kill|plant|defuse|capture|clutch_won)$|^flag_captured$|^round_won", "cheer"),
    (r"^reply_greeting$|^player_joined$|^teammate_joined$", "greeting"),
    (r"^reply_bye$", "goodbye"), (r"^match_(won|lost)$|^reply_gg$|^close_match_end$", "good_game"),
]

def concept_for(key):
    for pat, c in RULES:
        if re.search(pat, key):
            if c is None: continue
            return c
    return None

if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    keys = [l.split("\t")[0][1:] for l in open(src, encoding="utf-8") if l.startswith("@")]
    rows = [(k, concept_for(k)) for k in keys]
    used = sorted({c for _, c in rows if c})
    bad = [c for c in used if c not in CONCEPTS]
    assert not bad, bad
    with open(out + "/voice_map.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write("# situation<TAB>concept. Situations not listed have no radio line and are text only.\n")
        f.write("# Generated by voice_build.py. voice_check.py turns concepts into the game's real voice ids.\n")
        for k, c in rows:
            if c: f.write(f"{k}\t{c}\n")
    n = sum(1 for _, c in rows if c)
    print(f"{n} of {len(rows)} situations have a radio line, {len(used)} concepts used: {', '.join(used)}")
