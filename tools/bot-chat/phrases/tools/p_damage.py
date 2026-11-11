L = {}

L["damage_taken"] = {
"entry": """
hit
I'm hit
took one
tagged me
shot from {area}
they hit me {area}
fine, keep going
hit, still up
ow
someone shooting {area}
""",
"anchor": """
I'm hit.
Taking fire from {area}.
Hit, I'm okay.
Fire from {area}.
Took a hit, still holding.
Someone shooting from {area}.
Hit. Staying put.
""",
"lurker": """
hit
got tagged
someone {area} shot me
hit, they know I'm here
took one
""",
"support": """
I'm hit!
taking fire {area}
hit, I'm okay
shot from {area}, careful
took a hit, fine
""",
"marksman": """
Hit.
Taking fire, {area}.
Shot from {area}.
Hit, adjusting.
Someone's on me from {area}.
""",
}

L["damage_low"] = {
"entry": """
one shot
I'm one hp
low
super low
1hp lol
one shot left, still going
""",
"anchor": """
I'm low.
One shot left.
Low, playing safe.
Very low. Holding back.
Low health, need cover.
""",
"lurker": """
low
one shot
im 1hp
low, hiding
""",
"support": """
I'm low!
one shot guys
low, need someone
very low, careful
one shot, cover me
""",
"marksman": """
Low.
One shot.
Low, falling back.
One hit left.
""",
}

L["friendly_fire_did"] = {
"entry": """
sorry
my bad
oops
sry {name}
mb
my bad {name}
""",
"anchor": """
Sorry.
My mistake, sorry.
Sorry {name}.
That was me, sorry.
My bad.
""",
"lurker": """
sry
mb
oops
sorry {name}
""",
"support": """
Sorry {name}!
sorry sorry
my bad, sorry
oops sorry
sorry, you walked in front
""",
"marksman": """
Sorry.
My fault.
Sorry {name}.
That was mine. Sorry.
""",
}

L["friendly_fire_got"] = {
"entry": """
hey
yo
watch it
I'm on your team lol
stop
same team
""",
"anchor": """
Check your fire.
Friendly.
Same team.
Watch your fire, {name}.
That's me.
""",
"lurker": """
bro
hey
friendly
lol
""",
"support": """
friendly!
careful, that's me
hey, same team
watch your fire {name}
it's me!
""",
"marksman": """
Friendly.
Check fire.
Same team, {name}.
Watch your line.
""",
}

L["teammate_down"] = {
"entry": """
{name} down
{name} died {area}
lost {name}
{name} down, I'll trade
{name} dead {area}
they got {name}
""",
"anchor": """
{name} is down.
Lost {name} at {area}.
{name} down at {area}.
{name} down. Holding.
They got {name}.
""",
"lurker": """
{name} down
{name} died {area}
rip {name}
lost {name}
""",
"support": """
{name} down!
{name} died at {area}
lost {name}, trade him
{name} down, I'm coming
rip {name}
""",
"marksman": """
{name} down.
Lost {name}, {area}.
{name} is down.
They got {name} at {area}.
""",
}

L["dead_info"] = {
"entry": """
{area}
he's at {area}
{count} {area}
he's low {area}
he's one shot
nt me
unlucky
he was there {area}
sorry
""",
"anchor": """
He's at {area}.
{count} at {area}.
He's low, {area}.
I'm down. Watch {area}.
Sorry. {area}.
He's still at {area}.
""",
"lurker": """
{area}
he's {area}
{count} {area}
he's low
one shot {area}
they're all {area}
""",
"support": """
He's at {area}, low
{count} at {area}
sorry guys, {area}
he's one shot {area}
he's hurt, {area}
careful {area}
""",
"marksman": """
{area}.
He's at {area}.
{count} at {area}.
Low, {area}.
He's on {area}. Still.
""",
}
