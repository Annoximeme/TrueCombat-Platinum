# Extra variants for own actions, damage and objectives.
L = {}

L["kill_confirm"] = {
"entry": """
got him lets go
one down next
killed him
got that guy
he's down
dropped one
got one more
one less
he's done
got one {area}
another
sat him down
killed one, pushing
next one
got {enemy} lol
""",
"anchor": """
One down. Staying.
Got one at {area}.
He's down. Next.
One less.
Down, {area}.
Killed {enemy}.
Got him, reset.
One down, still here.
He's dead.
Got one. Watching for more.
""",
"lurker": """
got one {area}
killed {enemy} lol
one down, still hidden
got him, he never turned
dropped one {area}
got one quiet
one less
got him
""",
"support": """
got him guys
one down!
got one {area}
he's dead!
got {enemy}
one down, push
traded
got him, you're good
""",
"marksman": """
Down.
One less.
Got him, {area}.
Got {enemy}.
Dropped him.
Clean kill.
One down. Resetting.
Took {enemy}.
""",
}

L["moving_to"] = {
"entry": """
going {area} now
{area} lets go
pushing {area} on me
I'm heading {area}
going in {area}
""",
"anchor": """
Moving to {area}, slow.
I'll take {area}.
Going {area}, covering.
Heading to {area} now.
""",
"lurker": """
going {area} quiet
heading {area} btw
taking {area} alone
moving {area}
""",
"support": """
going {area} with you
heading to {area}
moving {area}, come
going {area} to help
""",
"marksman": """
Moving {area}.
Going to {area}, new angle.
Taking {area}.
Repositioning to {area}.
""",
}

L["holding"] = {
"entry": """
watching {area} for now
I'll sit {area} a bit
holding {area} they'll come
""",
"anchor": """
I'm holding {area}.
{area}'s mine, go.
Holding {area}. Don't worry about it.
Sitting {area}.
Watching {area}. Call me if needed.
""",
"lurker": """
sitting {area}
holding {area}, quiet
waiting {area}
""",
"support": """
holding {area} for us
I'm watching {area}
{area} covered
""",
"marksman": """
Holding {area}, scoped.
Watching {area}.
I have {area}.
On {area}, long.
""",
}

L["damage_taken"] = {
"entry": """
tagged me, I'm fine
hit, still going
got hit {area}
shot from {area}, pushing
ouch
""",
"anchor": """
Hit. I'm fine.
Took one from {area}.
I'm hit, holding.
Taking fire {area}.
""",
"lurker": """
hit
tagged
shot from {area}
hit, I'm spotted
""",
"support": """
hit, careful {area}
I'm hit, still good
got tagged {area}
taking fire from {area}!
""",
"marksman": """
Hit. Moving.
Fire from {area}.
Took one.
Shot from {area}, adjusting.
""",
}

L["teammate_down"] = {
"entry": """
{name} died, trading
they got {name} {area}
{name}'s down, going
{name} down, swinging
""",
"anchor": """
{name} is down at {area}.
Lost {name}. Holding.
{name} down. Careful.
""",
"lurker": """
{name} died
{name} down {area}
lost {name}
""",
"support": """
{name} died, trade!
{name} down {area}, careful
lost {name}, they're at {area}
{name}!! down
""",
"marksman": """
{name} down at {area}.
Lost {name}.
{name} is down. Watching {area}.
""",
}

L["dead_info"] = {
"entry": """
he's one shot {area}
{count} at {area}
sorry, wide swing
he's low go
he's {area}
""",
"anchor": """
He's at {area}. Low.
{count} at {area}. Careful.
He's one shot, {area}.
Sorry. He's at {area}.
""",
"lurker": """
{count} at {area}
sorry
he's {area}
low {area}
""",
"support": """
he's at {area}, one shot!
{count} at {area}, careful
he's hurt, {area}
sorry guys
""",
"marksman": """
He's at {area}. Low.
{count} at {area}.
One shot, {area}.
He's on {area}.
""",
}

L["need_help"] = {
"entry": """
need a trade {area}
come {area} now
someone {area} please
{area} help
""",
"anchor": """
I need help at {area}.
Pinned at {area}.
{area} is falling, help.
""",
"lurker": """
help {area}
need help
pinned
""",
"support": """
help at {area}!
need someone at {area}!
pinned {area}, help
""",
"marksman": """
Need help, {area}.
Pinned, {area}.
""",
}

L["round_plan_attack"] = {
"entry": """
{area} rush
going {area} with or without you
{area} lets go
I'm first {area}
fast {area}
""",
"anchor": """
I'll follow to {area}.
Going {area}, I'll hold the flank.
{area}. I'll stay back.
""",
"lurker": """
going {area}, don't wait
taking {area}
I'm {area}
""",
"support": """
{area}, I'll smoke
going {area}, I'm with you
{area}, flashes ready
""",
"marksman": """
{area}. Long angle.
Going {area}.
I'll cover {area}.
""",
}

L["round_plan_defend"] = {
"entry": """
going {area} early
I'll look for one {area}
pushing {area} for info
""",
"anchor": """
Holding {area}.
I've got {area}. Rotate if you hear them.
I'll anchor {area}.
""",
"lurker": """
I'll go {area}
hiding {area}
{area}
""",
"support": """
{area}, I'll help
{area} with you
I'll be near {area}
""",
"marksman": """
{area}, long.
Holding {area}.
Taking {area}.
""",
}
