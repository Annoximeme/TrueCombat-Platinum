"""Builds roster.json, roster.txt and ROSTER.md from the table below. Edit the table, run: python roster_build.py <outdir>"""
import json, sys, os
# name, personality, aggression, patience, teamplay, weapon, sniper, lean, crouch, jiggle, chatty, lower%, play quirk, chat quirk
R = [
("Viper","entry",95,15,55,"smg",0,30,20,60,85,90,"Always first through the door. Re-peeks the same angle once too often.","Never waits; types fast and lower-case."),
("Blaze","entry",90,20,45,"rifle",0,25,15,45,90,80,"Sprints the first 10 seconds of every round. Chases kills too far.","Loudest bot on the team. Celebrates every kill."),
("Havoc","entry",85,25,60,"shotgun",0,20,30,30,70,70,"Loves close corners and tight rooms. Weak at range.","Short and blunt."),
("Cobra","entry",80,35,65,"rifle",0,45,25,70,65,60,"Jiggle-peeks before committing. The careful entry.","Calls his peek before he takes it."),
("Jackal","entry",88,20,40,"smg",0,30,20,50,75,95,"Takes the fight even when outnumbered.","Cocky. Says 'ez' more than he should."),
("Vandal","entry",82,30,50,"rifle",0,35,20,40,60,75,"Pushes through smoke. Throws his frag early.","Announces every grenade."),
("Storm","entry",78,40,75,"rifle",0,40,30,45,80,50,"The entry who waits for the flash. Best paired with a support.","Asks for a flash, then goes."),

("Warden","anchor",25,95,70,"rifle",10,70,60,20,60,5,"Never leaves his site. Last to rotate.","Calm, full sentences, always a full stop."),
("Rook","anchor",30,90,65,"mg",0,50,70,10,50,10,"Locks one lane with the machine gun and stays crouched.","Few words. Reports, never chats."),
("Bishop","anchor",35,85,80,"rifle",15,75,50,30,65,5,"Holds the cross angle and covers the other anchor.","Gives the team instructions: 'Hold.', 'Don't peek.'"),
("Kodiak","anchor",40,80,60,"shotgun",0,40,55,15,45,15,"Sits close to the objective and makes you come to him.","Dry. Unbothered when he dies."),
("Sierra","anchor",30,88,85,"rifle",20,65,45,25,70,10,"Rotates early on good information. Plays the retake well.","Clear rotate calls. Thanks people for info."),
("Wolf","anchor",45,75,70,"rifle",5,60,40,35,55,20,"The anchor who takes one early pick, then falls back.","Tells you when he gives up ground."),

("Ghost","lurker",50,90,25,"smg",0,60,80,20,25,100,"Walks everywhere. Shows up behind you two minutes into the round.","Almost silent. When he talks, it matters."),
("Shadow","lurker",55,85,30,"rifle",10,65,75,25,35,100,"Waits for the team's push, then hits the back.","'give me 5 sec'. Timing talk."),
("Lynx","lurker",65,70,35,"smg",0,55,60,40,40,95,"Fast lurker. Takes the long way round at a run, then goes quiet.","Dry humour. 'lol' after a backstab."),
("Mamba","lurker",60,80,30,"rifle",0,70,70,30,30,100,"Sits in one off-angle per round and never the same one twice.","Tells you where he is hiding, once."),
("Nomad","lurker",45,75,45,"rifle",15,50,55,20,45,90,"Roams between lanes and feeds the team information.","More info calls than kills. Says 'btw' a lot."),
("Onyx","lurker",70,65,25,"shotgun",0,40,65,15,20,100,"Hides close to the bomb after the plant.","Barely speaks. One-word answers."),
("Reaper","lurker",75,60,30,"rifle",5,55,50,35,35,95,"Hunts the last enemy alive. Good in the clutch.","Quiet until the clutch, then asks for silence."),

("Sparrow","support",40,60,95,"smg",0,45,40,30,90,40,"Always second in. Throws the flash for the entry.","Friendliest bot. Thanks and encourages."),
("Tango","support",45,55,90,"rifle",0,50,35,35,85,45,"Smokes the crossing every round and re-smokes when it fades.","Counts down his utility."),
("Yankee","support",50,50,85,"rifle",0,40,30,40,80,50,"Trades the entry within a second or two.","'I'll trade you'. Calls who he is behind."),
("Frost","support",35,70,90,"rifle",10,55,50,25,70,30,"Stays with the bomb carrier and covers the plant.","Calm helper. Offers to carry or defuse."),
("Puma","support",55,45,80,"smg",0,35,25,45,85,60,"The aggressive support: flashes for himself when nobody goes.","Chatty. Apologises quickly."),
("Saber","support",45,65,88,"mg",0,40,55,20,65,35,"Suppresses a lane so others can cross.","'Covering, cross now.'"),

("Falcon","marksman",30,90,50,"sniper",95,80,40,20,45,5,"Holds the longest line on the map. Relocates after every shot.","Clipped. 'Mine.'"),
("Raven","marksman",35,85,55,"sniper",90,75,45,25,40,5,"Counter-sniper. Looks for the enemy scope first.","Calls the enemy sniper before anything else."),
("Talon","marksman",50,70,45,"sniper",85,60,30,50,50,15,"Aggressive scope. Peeks first, repositions late.","Admits his misses."),
("Mako","marksman",40,80,60,"rifle",60,70,50,30,45,10,"Rifle on single fire at range. Switches to the scope on long maps.","Talks range and lines."),
("Hunter","marksman",45,75,65,"sniper",80,65,60,20,55,20,"Covers the bomb from distance after the plant.","Tells the team which line he has."),
("Ranger","marksman",35,88,70,"rifle",50,70,55,25,50,10,"Overwatch for the entries. Shoots what they flush out.","'Go. I have the angle.'"),
]
cols = ["name","personality","aggression","patience","teamplay","weapon","sniper","lean","crouch","jiggle","chatty","lower","play","chat"]
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
rows = [dict(zip(cols, r)) for r in R]
assert len({r["name"] for r in rows}) == len(rows)
json.dump({"version": "1.0.0", "note": "Values are 0-100. chatty = chance to speak when chosen; lower = share of lines typed lower-case.", "bots": rows},
          open(f"{out}/roster.json", "w", encoding="utf-8", newline="\n"), indent=1)
with open(f"{out}/roster.txt", "w", encoding="utf-8", newline="\n") as f:
    f.write("# Bot roster 1.0.0. TAB-separated: " + " ".join(cols[:12]) + "\n")
    for r in rows: f.write("\t".join(str(r[c]) for c in cols[:12]) + "\n")
with open(f"{out}/ROSTER.md", "w", encoding="utf-8", newline="\n") as f:
    f.write("# Bot roster 1.0.0\n\nThe 32 existing bot names, each with a fixed personality that stays the same across matches, so regulars can learn them.\n"
            "Numbers are 0 to 100. They multiply the utility weights of the bot brain (design idea 7); `chatty` and `lower` feed the chat picker.\n"
            "Edit the table in `tools/roster_build.py` and rebuild.\n")
    for pers in ["entry","anchor","lurker","support","marksman"]:
        f.write(f"\n## {pers.capitalize()}\n\n| Bot | Plays like | Sounds like | Weapon | Aggr. | Patience | Team | Chatty |\n|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            if r["personality"] == pers: f.write(f"| **{r['name']}** | {r['play']} | {r['chat']} | {r['weapon']} | {r['aggression']} | {r['patience']} | {r['teamplay']} | {r['chatty']} |\n")
    f.write("\n## Team mix\n\nWhen filling a team, pick one of each personality before repeating one: entry, support, anchor, lurker, marksman.\n"
            "A five-bot team then has every voice in chat and every role on the map. On maps with no long lines, swap the marksman for a second support.\n")
print(len(rows), "bots")
