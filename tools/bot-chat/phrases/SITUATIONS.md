# Situation index (phrase bank 1.4.0)

323 situations, 8829 lines. `always` placeholders are filled every time; `maybe` only when known.


## contact

| Key | Fires when | Channel | Cooldown | Always | Maybe | Lines |
|---|---|---|---|---|---|---|
| `contact_one` | Bot sees a single enemy for the first time this contact. | team | 6 | {area} | - | 179 |
| `contact_many` | Bot sees two or more enemies together. | team | 6 | {area} {count} | - | 147 |
| `contact_sniper` | Bot spots an enemy with a scoped rifle. | team | 15 | {area} | - | 57 |
| `contact_lost` | Enemy broke line of sight; last known area. | team | 10 | {area} | - | 79 |
| `enemy_heard` | Bot heard footsteps, a reload or a door, but saw nothing. | team | 12 | {area} | - | 68 |
| `enemy_rotating` | Belief map says enemies are moving toward an area. | team | 20 | {area} | - | 50 |
| `enemy_low` | Bot hit an enemy hard who got away. | team | 8 | {area} | - | 48 |
| `enemies_left` | Enemy count update when several are still alive. | team | 15 | {count} | - | 45 |
| `last_enemy` | Only one enemy left alive. | team | 15 | - | {area} | 55 |
| `area_clear` | Bot checked an area and found nobody. | team | 15 | {area} | - | 46 |
| `grenade_incoming` | Enemy grenade landed near the bot and teammates. | team | 4 | - | - | 34 |
| `smoke_seen` | Enemy smoke popped in an area. | team | 20 | {area} | - | 32 |
| `enemy_behind` | An enemy appeared behind the team (flank detected). | team | 8 | - | {area} | 35 |
| `enemy_above` | Enemy is on a roof, balcony, window or upper floor. | team | 10 | {area} | - | 23 |
| `enemy_below` | Enemy is under the bot (lower floor, pit, stairs). | team | 10 | {area} | - | 23 |
| `enemy_prone` | Enemy lying prone, easy to miss. | team | 12 | {area} | - | 23 |
| `enemy_camping` | Enemy has been holding the same spot for a long time. | team | 20 | {area} | - | 21 |
| `enemy_pushing` | Enemies are actively rushing an area. | team | 8 | {area} | {count} | 29 |
| `enemy_fake` | The bot believes the noise at an area is a fake. | team | 20 | {area} | - | 20 |
| `enemy_saving` | Remaining enemies are hiding to run the clock. | team | 30 | - | {area} | 24 |
| `enemy_in_spawn` | Enemy reached the bot team's spawn. | team | 15 | - | - | 21 |
| `enemy_grenade_seen` | Enemy used a frag or flash at an area (info, not danger). | team | 15 | {area} | - | 20 |
| `enemy_through_smoke` | Enemies are coming through smoke. | team | 10 | {area} | - | 21 |
| `contact_close` | Enemy is very close (same room, around the corner). | team | 6 | - | {area} | 24 |
| `contact_far` | Enemy seen at long range. | team | 10 | {area} | - | 22 |
| `enemy_weapon_info` | Enemy has a notable weapon (shotgun or machine gun) at an area. | team | 20 | {area} | - | 21 |
| `numbers_advantage` | Bot's team has clearly more players alive. | team | 30 | - | - | 24 |
| `numbers_disadvantage` | Bot's team is clearly outnumbered. | team | 30 | - | - | 25 |
| `enemy_reload_heard` | Bot heard an enemy reloading: chance to push. | team | 10 | - | {area} | 30 |
| `enemy_jiggling` | Enemy keeps shoulder-peeking the same corner. | team | 15 | {area} | - | 20 |
| `enemy_on_ladder` | Enemy on a ladder: easy target. | team | 15 | {area} | - | 20 |
| `enemy_in_water` | Enemy swimming or wading. | team | 20 | {area} | - | 20 |
| `enemy_lone` | A lone enemy far from his team: go get him together. | team | 20 | {area} | - | 25 |
| `contact_unaware` | Bot sees an enemy who has not noticed it (not facing the bot, notice state idle). Beats contact_one and contact_many. | team | 8 | {area} | {count} | 46 |
| `contact_running` | Bot sees an enemy sprinting. | team | 8 | {area} | - | 24 |
| `contact_sneaking` | Bot sees an enemy walking or crouched (moving quietly). | team | 8 | {area} | {count} | 34 |
| `contact_static` | Bot sees an enemy who is standing still or holding a spot. | team | 10 | {area} | {count} | 30 |
| `enemy_heard_door` | Bot heard a door open or close. | team | 15 | {area} | - | 23 |

## action

| Key | Fires when | Channel | Cooldown | Always | Maybe | Lines |
|---|---|---|---|---|---|---|
| `kill_confirm` | Bot got a kill. | team | 5 | - | {area} {enemy} | 125 |
| `kill_multi` | Bot got two or more kills in quick succession. | team | 10 | - | - | 42 |
| `kill_headshot` | Bot got a headshot kill. | team | 10 | - | - | 33 |
| `moving_to` | Bot is heading to an area on its own plan. | team | 15 | {area} | - | 65 |
| `holding` | Bot sets up to hold an area. | team | 20 | {area} | - | 62 |
| `flanking` | Bot is going round the back. | team | 25 | {area} | - | 37 |
| `falling_back` | Bot retreats. | team | 12 | - | {area} | 51 |
| `reloading` | Bot reloads with enemies nearby. | team | 10 | - | - | 33 |
| `need_help` | Bot is outnumbered or pinned and asks for help. | team | 15 | {area} | - | 54 |
| `throw_frag` | Bot throws a frag grenade. | team | 6 | - | {area} | 32 |
| `throw_smoke` | Bot throws smoke. | team | 10 | - | {area} | 29 |
| `throw_flash` | Bot throws a flash or stun grenade. | team | 6 | - | - | 25 |
| `enemy_spawn_reached` | Bot reached the enemy spawn area. | team | 30 | - | - | 25 |
| `execute_ready` | Bot is at the gather point, waiting for the go. | team | 15 | - | {area} | 27 |
| `execute_wait` | Bot asks the team to wait (teammates not in position, utility not out). | team | 15 | - | - | 24 |
| `execute_go` | The synchronised push starts. | team | - | - | {area} | 29 |
| `entry_going` | Bot is the first through a door or chokepoint. | team | 10 | - | {area} | 26 |
| `trade_ready` | Bot is right behind a teammate ready to trade. | team | 12 | {name} | - | 21 |
| `traded` | Bot killed the enemy who just killed a teammate. | team | 6 | {name} | {enemy} | 21 |
| `covering` | Bot is covering a teammate or an angle so others can move. | team | 12 | - | {area} {name} | 24 |
| `crossing` | Bot is about to cross an open line. | team | 12 | - | {area} | 21 |
| `peeking` | Bot is about to peek a held angle. | team | 10 | - | {area} | 22 |
| `watching_back` | Bot watches the flank or rear. | team | 25 | - | {area} | 22 |
| `low_ammo` | Bot is low on ammunition. | team | 30 | - | - | 22 |
| `out_of_ammo` | Bot's primary is empty; switching to sidearm. | team | 30 | - | - | 23 |
| `weapon_pickup` | Bot picked up a dropped weapon. | team | 30 | - | - | 25 |
| `no_utility` | Bot has no grenades left for what's needed. | team | 30 | - | - | 25 |
| `ask_smoke` | Bot asks a teammate to smoke an area. | team | 20 | {area} | - | 25 |
| `ask_flash` | Bot asks for a flash before peeking. | team | 20 | - | {area} | 24 |
| `going_quiet` | Bot starts sneaking (walking, crouching). | team | 30 | - | - | 25 |
| `door_open` | Bot is about to open a door (noise warning). | team | 30 | - | {area} | 25 |
| `ladder` | Bot is climbing; exposed for a moment. | team | 40 | - | - | 25 |
| `blocked_by_teammate` | A teammate is blocking the bot's path or line of fire. | team | 20 | - | {name} | 24 |
| `in_the_way_sorry` | Bot was blocking a teammate. | team | 20 | - | - | 25 |
| `stay_together` | Bot suggests grouping up. | team | 40 | - | - | 23 |
| `spread_out` | Team is clumped; grenade risk. | team | 40 | - | - | 25 |
| `quiet_round` | Long silence, no contact so far. | team | 45 | - | - | 21 |
| `ask_info` | Bot asks teammates what they saw. | team | 30 | - | {area} | 22 |
| `kill_knife` | Bot got a knife kill. | all | 20 | - | {enemy} | 23 |
| `kill_grenade` | Bot's grenade killed someone. | team | 15 | - | {area} | 22 |
| `kill_pistol` | Bot got a kill with its sidearm. | team | 15 | - | - | 24 |
| `kill_long` | Kill at long range. | team | 15 | - | {area} | 28 |
| `kill_wallbang` | Kill through a wall or cover. | team | 20 | - | - | 25 |
| `kill_through_smoke` | Kill through smoke. | team | 20 | - | - | 25 |
| `kill_low_hp` | Bot won a fight while almost dead. | team | 20 | - | - | 24 |
| `kill_last` | Bot killed the last enemy and won the round. | team | - | - | - | 23 |
| `kill_sniper` | Bot killed the enemy sniper. | team | 15 | - | {area} | 26 |
| `kill_flanker` | Bot caught an enemy flanking. | team | 15 | - | {area} | 23 |
| `missed_shot` | Bot whiffed an easy kill. | team | 30 | - | - | 24 |
| `missed_scope` | Marksman-style miss with a bolt action. | team | 30 | - | - | 27 |
| `assist` | Teammate finished someone the bot damaged. | team | 20 | {name} | - | 23 |
| `kill_stolen` | Friendly banter: a teammate took the bot's kill. | team | 40 | {name} | - | 24 |
| `saved_by_teammate` | A teammate killed someone about to kill the bot. | team | 20 | {name} | - | 23 |
| `saved_teammate` | Bot killed someone about to kill a teammate. | team | 20 | {name} | - | 25 |
| `revenge` | Bot killed the player who killed it last round. | all | 30 | - | {enemy} | 24 |
| `nobody_coming` | Bot has held an area for a long time with no contact. | team | 40 | {area} | - | 20 |
| `rotating_self` | Bot itself rotates. | team | 20 | {area} | - | 20 |
| `arriving` | Bot is about to arrive to help. | team | 15 | - | {area} | 20 |
| `friendly_smoke_block` | Team's own smoke blocks the bot's view. | team | 30 | - | - | 20 |
| `out_of_breath` | Stamina is empty. | team | 60 | - | - | 20 |
| `stuck` | Bot's stall watchdog fired: it is stuck. Honest and useful for bug reports. | team | 30 | - | {area} | 20 |
| `smoke_fading` | Team's smoke is about to clear. | team | 30 | - | {area} | 20 |
| `second_smoke` | Bot throws a follow-up smoke. | team | 30 | - | {area} | 20 |
| `nade_missed` | Bot's grenade did nothing. | team | 30 | - | - | 20 |
| `enemy_flash_dodged` | Bot turned away from a flash in time. | team | 30 | - | - | 20 |
| `kill_unaware` | Bot killed an enemy who never noticed it. | team | 8 | - | {area} {enemy} | 30 |
| `flag_going` | Flag modes: bot is heading for the enemy flag. | team | 25 | - | {area} | 24 |
| `flag_defend` | Flag modes: bot is staying back to guard its own flag. | team | 30 | - | - | 21 |

## damage

| Key | Fires when | Channel | Cooldown | Always | Maybe | Lines |
|---|---|---|---|---|---|---|
| `damage_taken` | Bot took a hit but is fine. | team | 8 | - | {area} | 76 |
| `damage_low` | Bot is very low on health. | team | 12 | - | - | 37 |
| `friendly_fire_did` | Bot hit a teammate. | team | 10 | - | {name} | 32 |
| `friendly_fire_got` | A teammate hit the bot. | team | 10 | - | {name} | 33 |
| `teammate_down` | A teammate died near the bot. | team | 8 | {name} | {area} | 52 |
| `dead_info` | Bot just died and passes on what it knew. | team | - | - | {area} {count} | 37 |
| `suppressed` | Bot is being suppressed and can't peek. | team | 12 | - | {area} | 24 |
| `flashed` | Bot is blinded by a flash or stun. | team | 8 | - | - | 23 |
| `team_flashed` | A teammate's flash blinded the bot. | team | 15 | - | {name} | 23 |
| `hit_through_wall` | Bot was hit through a wall or thin cover. | team | 15 | - | {area} | 22 |
| `fall_damage` | Bot took fall damage or a bad jump. | team | 30 | - | - | 24 |
| `died_first` | Bot was the first to die this round. | team | - | - | {area} | 22 |
| `died_to_grenade` | Bot died to a grenade. | team | - | - | - | 25 |
| `died_to_sniper` | Bot died to a sniper. | team | - | - | {area} | 25 |
| `died_from_behind` | Bot was shot in the back. | team | - | - | {area} | 24 |
| `died_in_duel` | Bot lost a straight fight. | team | - | - | {area} | 25 |
| `died_reloading` | Bot died while reloading. | team | - | - | - | 25 |
| `died_to_teamkill` | A teammate killed the bot. | team | - | - | {name} | 24 |
| `teamkilled_someone` | Bot killed a teammate by accident. | team | - | - | {name} | 24 |
| `nade_own_team` | Bot's grenade landed near teammates. | team | 30 | - | - | 25 |
| `dead_enemy_low` | Bot died after dealing heavy damage to its killer (50 or more). Beats dead_info. | team | - | - | {area} | 38 |

## objective

| Key | Fires when | Channel | Cooldown | Always | Maybe | Lines |
|---|---|---|---|---|---|---|
| `round_plan_attack` | Round start, attacking side, bot states where it is going. | team | - | {area} | - | 48 |
| `round_plan_defend` | Round start, defending side, bot states what it holds. | team | - | {area} | - | 38 |
| `bomb_pickup` | Bot picked up the bomb. | team | - | - | - | 28 |
| `bomb_planting` | Bot starts planting. | team | - | - | {area} | 28 |
| `bomb_planted` | Bomb is down (bot or teammate planted). | team | - | {area} | - | 29 |
| `bomb_defusing` | Bot starts defusing. | team | - | - | - | 23 |
| `bomb_dropped` | The carrier died and the bomb is on the ground. | team | 10 | {area} | - | 24 |
| `enemy_bomb_planted` | Enemies planted; bot wants a retake. | team | - | {area} | - | 27 |
| `flag_taken` | Bot took the enemy flag. | team | - | - | - | 26 |
| `flag_lost` | Enemy took our flag. | team | - | - | {area} | 25 |
| `flag_captured` | Our team captured. | team | - | - | - | 25 |
| `rotate_call` | Bot tells the team to rotate. | team | 20 | {area} | - | 26 |
| `time_low` | Little time left in the round and the bot's side must act. | team | 30 | - | - | 26 |
| `enemy_bomb_carrier` | Bot spots the enemy carrying the bomb. | team | 10 | {area} | - | 24 |
| `enemy_planting` | Enemy is planting right now. | team | - | - | {area} | 24 |
| `enemy_defusing` | Enemy is on the bomb defusing. | team | - | - | - | 24 |
| `enemy_defuse_fake` | Enemy tapped the bomb and got off (fake defuse). | team | - | - | - | 21 |
| `enemy_flag_carrier` | Bot sees the enemy carrying our flag. | team | 8 | {area} | - | 21 |
| `post_plant_pos` | Bot says where it holds after the plant. | team | - | {area} | - | 21 |
| `play_time` | Bot's team is ahead on the clock and should not peek. | team | 30 | - | - | 21 |
| `save_call` | Bomb modes: the bomb can no longer be defused in time; bot tells the team to get clear instead of dying to it. | team | - | - | - | 21 |
| `bomb_ticking` | Bomb timer is nearly out. | team | 20 | - | - | 21 |
| `need_defuser_cover` | Bot wants to defuse and needs cover first. | team | - | - | - | 25 |
| `who_defuses` | Bot tells a teammate to defuse while it covers. | team | - | {name} | - | 25 |
| `bomb_take_offer` | Bot offers to pick up or carry the bomb. | team | - | - | - | 25 |
| `bomb_site_choice` | Carrier announces which site. | team | - | {area} | - | 24 |
| `flag_carrier_escort` | Bot escorts a teammate with the flag. | team | 15 | {name} | - | 25 |
| `flag_returned` | Our flag was returned. | team | - | - | - | 25 |
| `flag_dropped` | A flag is on the ground. | team | 8 | - | {area} | 25 |
| `point_capturing` | Point Capture mode: bot is on the point. | team | 20 | - | {area} | 23 |
| `point_contested` | Enemies are contesting or taking the point. | team | 15 | - | {count} | 22 |
| `kill_carrier` | Bomb modes: bot killed the enemy bomb carrier. (Flag carrier: kill_flag_carrier.) | team | - | - | {area} | 23 |
| `kill_defuser` | Bot killed someone on the bomb. | team | - | - | - | 24 |
| `time_60` | One minute left in the round. | team | - | - | - | 22 |
| `time_30` | Thirty seconds left. | team | - | - | - | 21 |
| `time_10` | Ten seconds left. | team | - | - | - | 21 |
| `site_taken` | Attackers control the site. | team | - | {area} | - | 23 |
| `site_lost` | Defenders lost the site. | team | - | {area} | - | 20 |
| `retake_start` | Team begins a retake. | team | - | {area} | - | 20 |
| `retake_done` | Site retaken, bomb is safe to defuse. | team | - | - | {area} | 20 |
| `carrier_needs_escort` | Bot carries the objective and is alone. | team | 15 | - | - | 20 |
| `bomb_site_empty` | Carrier found the site empty. | team | - | {area} | - | 20 |
| `bomb_guard` | Bot guards the dropped bomb. | team | 20 | {area} | - | 20 |
| `heard_plant` | Bot heard the plant sound without seeing it. | team | - | - | {area} | 22 |
| `heard_defuse` | Bot heard the defuse. | team | - | - | - | 24 |
| `kill_flag_carrier` | Flag modes: bot killed the enemy who was carrying our flag. | team | - | - | {area} | 26 |
| `flag_standoff` | Flag modes: we hold their flag but cannot capture because they hold ours. | team | 20 | - | - | 20 |
| `flag_enemy_returned` | Flag modes: the enemy returned their own flag after we dropped it. | team | - | - | - | 20 |
| `flag_enemy_captured` | Flag modes: the enemy captured our flag. | team | - | - | - | 20 |
| `time_hold` | Little time left and the clock favours the bot's side (defenders before a plant, a team ahead on score). | team | 30 | - | - | 21 |

## clutch

| Key | Fires when | Channel | Cooldown | Always | Maybe | Lines |
|---|---|---|---|---|---|---|
| `clutch_start` | Bot is the last alive on its team. | team | - | - | {count} | 46 |
| `clutch_won` | Bot won the round as the last one alive. | team | - | - | - | 29 |
| `clutch_lost` | Bot lost the round as the last one alive. | team | - | - | - | 24 |
| `human_clutch_cheer` | A human teammate is the last alive (dead bots cheering). | team | - | {name} | - | 23 |
| `human_clutch_won` | A human teammate won a clutch. | team | - | {name} | - | 26 |

## round

| Key | Fires when | Channel | Cooldown | Always | Maybe | Lines |
|---|---|---|---|---|---|---|
| `round_won` | Team won the round. | team | - | - | - | 62 |
| `round_lost` | Team lost the round. | team | - | - | - | 51 |
| `round_lost_streak` | Team lost three or more in a row. | team | - | - | - | 27 |
| `match_won` | Match over, bot's team won. | all | - | - | - | 27 |
| `match_lost` | Match over, bot's team lost. | all | - | - | - | 24 |
| `warmup` | Warm-up chatter while waiting. | all | 60 | - | - | 39 |
| `player_joined` | A human joins the server. | all | 30 | {name} | - | 23 |
| `nice_shot_teammate` | A human teammate got a great kill or a multi-kill. | team | 20 | {name} | - | 27 |
| `killed_by_good` | Bot died to a clean shot from a human. | all | 30 | - | {enemy} | 28 |
| `killed_by_cheap` | Bot died to something annoying (spray through smoke, nade, camping). | all | 60 | - | - | 24 |
| `on_fire` | Bot is on a kill streak; confident mood. | team | 60 | - | - | 25 |
| `cold_streak` | Bot keeps dying; self-deprecating. | team | 90 | - | - | 24 |
| `dominated_by` | The same human keeps killing the bot. Respectful. | all | 120 | {enemy} | - | 24 |
| `round_start_generic` | Round start, no specific plan to announce. | team | - | - | - | 44 |
| `first_round` | First round of the match. | all | - | - | - | 24 |
| `match_point_us` | Bot's team needs one more round to win. | team | - | - | - | 24 |
| `match_point_them` | Enemy needs one more round to win. | team | - | - | - | 24 |
| `last_round` | Final round of the match, score decides it. | team | - | - | - | 25 |
| `score_tied` | Score is level. | team | - | - | - | 25 |
| `comeback` | Team has won several in a row after being behind. | team | - | - | - | 24 |
| `big_lead` | Team is far ahead. No gloating at the enemy. | team | - | - | - | 25 |
| `far_behind` | Team is far behind. Encouraging. | team | - | - | - | 25 |
| `flawless_round` | Team won the round without losing anyone. | team | - | - | - | 24 |
| `close_round_won` | Won a round with one player left or seconds on the clock. | team | - | - | - | 24 |
| `round_won_time` | Won because the clock ran out. | team | - | - | - | 25 |
| `round_lost_time` | Lost because the clock ran out. | team | - | - | - | 25 |
| `round_won_bomb` | Won by detonation or defuse. | team | - | - | - | 25 |
| `side_switch` | Teams switch sides at half. | all | - | - | - | 25 |
| `overtime` | Match goes to extra rounds. | all | - | - | - | 24 |
| `teammate_joined` | A human joined the bot's team. | team | 30 | {name} | - | 25 |
| `teammate_left` | A teammate disconnected. | team | 60 | - | {name} | 25 |
| `enemy_left` | An enemy disconnected; teams uneven. | all | 60 | - | - | 25 |
| `auto_balanced` | Bot was moved to the other team. | all | 60 | - | - | 25 |
| `bot_replaced` | Bot is about to leave because a human took the slot. | all | - | - | {name} | 25 |
| `vote_called` | A vote was called. | all | 60 | - | - | 25 |
| `map_voted_good` | Next map chosen and the bot "likes" it. | all | - | - | - | 25 |
| `map_start` | New map just loaded. | all | - | - | - | 25 |
| `afk_teammate` | A teammate hasn't moved. Polite. | team | 120 | {name} | - | 25 |
| `waiting_for_players` | Warm-up, server waiting for more humans. | all | 120 | - | - | 25 |
| `human_first_blood` | Human teammate got the opening kill. | team | 30 | {name} | - | 25 |
| `human_multi_kill` | Human teammate got three or more. | team | 20 | {name} | - | 24 |
| `human_plant` | Human teammate planted. | team | - | {name} | - | 25 |
| `human_defuse` | Human teammate defused. | team | - | {name} | - | 25 |
| `human_capture` | Human teammate captured the flag or point. | team | - | {name} | - | 25 |
| `human_died_unlucky` | Human teammate died in a way that wasn't their fault. | team | 30 | {name} | - | 25 |
| `top_fragger_bot` | Match end, bot was top of the board. Modest. | all | - | - | - | 25 |
| `top_fragger_human` | Match end, a human was top of the board. | all | - | {name} | - | 25 |
| `close_match_end` | Match ended by one or two rounds. | all | - | - | - | 25 |
| `rematch` | After the match. | all | - | - | - | 25 |
| `weapon_choice_sniper` | Round start: bot took a scoped rifle. | team | - | - | - | 20 |
| `weapon_choice_shotgun` | Round start: bot took a shotgun. | team | - | - | - | 20 |
| `weapon_choice_mg` | Round start: bot took a machine gun. | team | - | - | - | 20 |
| `respawned` | Respawn modes: bot is back. | team | 20 | - | - | 20 |
| `spawn_killed` | Bot died right after spawning. | all | 60 | - | - | 20 |
| `lead_taken` | Respawn or capture modes: team took the lead. | team | - | - | - | 20 |
| `lead_lost` | Team lost the lead. | team | - | - | - | 20 |
| `humans_arguing` | Two teammates are arguing in chat. Bot calms things once. | team | 120 | - | - | 20 |
| `human_tk_seen` | A human teammate killed another by accident. | team | 60 | - | - | 20 |
| `vote_kick_bot` | A vote to remove the bot passed. | all | - | - | - | 20 |
| `late_join_round` | Bot joined mid-round and waits. | team | - | - | - | 20 |
| `round_won_detonated` | Attackers won because the bomb went off. | team | - | - | - | 21 |
| `round_won_defused` | Defenders won by defusing. | team | - | - | - | 20 |
| `kills_to_win` | Deathmatch: bot's team needs only {count} more kills to win (fire at 5 or fewer). | team | 30 | {count} | - | 20 |

## orders

| Key | Fires when | Channel | Cooldown | Always | Maybe | Lines |
|---|---|---|---|---|---|---|
| `order_follow` | Human told the bot to follow them. | team | - | {name} | - | 30 |
| `order_hold` | Human told the bot to hold. | team | - | - | {area} | 27 |
| `order_push` | Human told the bot to push now. | team | - | - | {area} | 27 |
| `order_goto` | Human told the bot to go to an area or lane. | team | - | {area} | - | 25 |
| `order_regroup` | Human told the bot to regroup. | team | - | - | - | 21 |
| `order_done` | Bot reached the ordered spot. | team | - | {area} | - | 21 |
| `order_busy` | Bot can't do the order right now (in a fight, pinned, carrying). | team | - | - | - | 26 |
| `order_unclear` | Bot could not parse the command. | team | - | - | - | 23 |
| `ping_enemy_ack` | Human pinged an enemy; bot acknowledges and looks. | team | 6 | {area} | - | 26 |
| `ping_help_ack` | Human pinged 'need help'; bot is coming. | team | 6 | {name} | - | 22 |
| `ping_cancel` | Human cancelled an order; bot goes back to its own plan. | team | - | - | - | 22 |
| `squad_leader` | A human became squad leader for the bots. | team | - | {name} | - | 22 |
| `reply_thanks` | Human thanked or complimented the bot. | team | 20 | - | - | 25 |
| `reply_greeting` | Human said hi to the bot or the server. | all | 30 | - | {name} | 23 |
| `reply_sorry` | Human apologised to the bot (team damage, bad call). | team | 20 | - | {name} | 21 |
| `order_cover_me` | Human asked the bot to cover them. | team | - | {name} | - | 25 |
| `order_watch` | Human asked the bot to watch an area or angle. | team | - | {area} | - | 25 |
| `order_smoke` | Human asked for a smoke; bot has one. | team | - | - | {area} | 25 |
| `order_flash` | Human asked for a flash; bot has one. | team | - | - | - | 25 |
| `order_frag` | Human asked for a grenade on a spot. | team | - | - | {area} | 25 |
| `order_no_utility` | Human asked for utility the bot doesn't have. | team | - | - | - | 25 |
| `order_drop_bomb` | Human asked the bot to drop the bomb. | team | - | - | {name} | 25 |
| `order_take_bomb` | Human asked the bot to pick up or carry the bomb. | team | - | - | - | 25 |
| `order_plant` | Human told the bot to plant. | team | - | - | {area} | 25 |
| `order_defuse` | Human told the bot to defuse. | team | - | - | - | 25 |
| `order_spread` | Human told bots to spread out. | team | - | - | - | 25 |
| `order_quiet` | Human told bots to walk or stop making noise. | team | - | - | - | 25 |
| `order_flank` | Human told the bot to flank. | team | - | - | {area} | 24 |
| `order_wait` | Human said wait. | team | - | - | - | 25 |
| `order_fallback` | Human told the bot to fall back. | team | - | - | {area} | 25 |
| `order_lead` | Human told the bot to go first. | team | - | - | - | 24 |
| `order_stack` | Human told bots to stack one site or area. | team | - | {area} | - | 25 |
| `order_declined_role` | Bot is the carrier, defusing, or last alive and can't follow the order. | team | - | - | - | 25 |
| `order_too_far` | Bot is too far away to help in time. | team | - | - | - | 25 |
| `order_dead` | Human gave an order to a dead bot. | team | - | - | - | 25 |
| `ask_status_reply` | Human asked where the bot is or what it's doing. | team | - | {area} | - | 23 |
| `ask_count_reply` | Human asked how many enemies; bot knows. | team | - | {count} | {area} | 24 |
| `ask_unknown_reply` | Human asked something the bot has no info on. | team | - | - | - | 25 |
| `ask_bomb_reply` | Human asked who has the bomb or where it is. | team | - | - | {area} {name} | 25 |
| `reply_are_you_bot` | Human asks if it's a bot. Always honest. | all | 60 | - | - | 23 |
| `reply_compliment` | Human complimented the bot's play. | all | 30 | - | {name} | 24 |
| `reply_insult` | Human flamed the bot. Bot stays calm and friendly, never hits back. | all | 60 | - | - | 24 |
| `reply_blame` | Human blamed the bot for losing the round. | team | 60 | - | - | 25 |
| `reply_gg` | Human said gg. | all | 20 | - | - | 24 |
| `reply_glhf` | Human said glhf. | all | 30 | - | - | 24 |
| `reply_bye` | Human said goodbye. | all | 30 | - | {name} | 24 |
| `reply_laugh` | Human laughed at something that happened. | all | 40 | - | - | 24 |
| `reply_nice_try` | Human said nt after the bot failed. | team | 30 | - | - | 25 |
| `reply_question_generic` | Human asked the bot something it can't answer. Short, honest. | all | 60 | - | - | 25 |
| `ping_go_here_ack` | Human pinged 'go here'. | team | - | {area} | - | 25 |
| `ping_watch_ack` | Human pinged 'watch here'. | team | - | {area} | - | 25 |
| `ping_danger_ack` | Human pinged danger on an area. | team | 8 | {area} | - | 25 |
| `ping_bomb_ack` | Human pinged the bomb or a site. | team | - | - | {area} | 25 |
| `human_call_thanks` | A human's call-out led to a kill for the bot. | team | 30 | {name} | - | 25 |
| `human_wrong_call` | A human's call turned out wrong. Neutral, no blame. | team | 60 | - | {area} | 25 |
| `called_by_name` | Human typed the bot's name with nothing else. | all | 30 | - | {name} | 20 |

## followup

| Key | Fires when | Channel | Cooldown | Always | Maybe | Lines |
|---|---|---|---|---|---|---|
| `fu_still_there` | Needs: this bot called an enemy at {area} in the last 20 s and still sees one there. | team | 12 | {area} | - | 25 |
| `fu_count_update` | Needs: this bot or a teammate called a count at an area in the last 15 s and the count changed. | team | 8 | {count} | {area} | 25 |
| `fu_found_again` | Needs: this bot said contact_lost in the last 30 s and has now reacquired the enemy. | team | 10 | {area} | - | 25 |
| `fu_same_spot_last_round` | Needs: per-round memory of where enemies were first seen or where this bot died; an enemy is at the same area again. | team | - | {area} | - | 25 |
| `fu_enemy_same_plan` | Needs: the commander's record that the enemy hit the same area in two or more rounds running. | team | - | {area} | - | 25 |
| `fu_called_it` | Needs: this bot predicted something (enemy_rotating, enemy_fake, enemy_behind) and it was confirmed within 20 s. | team | 60 | - | {area} | 25 |
| `fu_my_call_wrong` | Needs: this bot's own call (fake, rotation, area clear) turned out wrong within 20 s. | team | 60 | - | {area} | 25 |
| `fu_not_clear_after_all` | Needs: this bot said area_clear for {area} in the last 30 s and now sees an enemy there. | team | 30 | {area} | - | 20 |
| `fu_got_the_called_one` | Needs: this bot killed an enemy a teammate called or pinged in the last 15 s. | team | 10 | - | {area} {name} | 25 |
| `fu_still_holding` | Needs: this bot announced holding {area} more than 45 s ago and is still there. | team | 60 | {area} | - | 21 |
| `fu_ack_teammate_call` | Needs: another bot or human on the team made a contact call near this bot in the last 3 s. Makes chat read like a conversation; one reply per call at most. | team | 8 | - | {area} {name} | 28 |
| `fu_answer_need_help` | Needs: a teammate (bot or human) said need_help or pinged for help, and this bot is the one sent. | team | 10 | {name} | {area} | 25 |
| `fu_cant_help` | Needs: a teammate asked for help and no bot can go; the nearest says so once. | team | 10 | {name} | - | 20 |
| `fu_answer_ask_info` | Needs: a teammate asked for info (ask_info or a human question) and this bot has nothing or something. | team | 15 | - | {area} | 20 |
| `fu_thanks_teammate` | Needs: a teammate did what this bot asked (smoke, flash, cover, help) in the last 10 s. | team | 30 | {name} | - | 20 |
| `fu_there_we_go` | Needs: this bot said missed_shot or cold_streak earlier and has now got a kill. | team | 60 | - | - | 20 |
| `fu_better_round` | Needs: the team lost the previous round (or several) and won this one. | team | - | - | - | 20 |
| `fu_go_slower` | Needs: this bot died first in two rounds running; said at the next round start. | team | - | - | - | 20 |
| `fu_still_on_order` | Needs: a human repeated an order this bot is already carrying out. | team | - | - | {area} | 20 |
| `fu_order_result` | Needs: an order from a human led to a kill or a won fight within 15 s. | team | - | - | {area} {name} | 20 |
| `fu_plan_change` | Needs: the commander picked a different plan from last round after a loss. | team | - | - | {area} | 20 |
| `fu_plan_repeat` | Needs: the commander picked the same plan again after a win. | team | - | - | {area} | 20 |
