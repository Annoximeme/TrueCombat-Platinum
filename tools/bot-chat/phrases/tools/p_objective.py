L = {}

L["round_plan_attack"] = {
"entry": """
going {area}
I'm entry {area}
{area}, I go first
rush {area}?
{area} fast
taking {area}
going {area} follow me
first in {area}
lets hit {area}
""",
"anchor": """
I'll come {area}.
Going {area}, behind the push.
{area}, I'll hold the back.
Taking {area} slow.
I'll watch our back through {area}.
Going {area}.
""",
"lurker": """
going {area}
I'll go {area}
taking {area} alone
{area}, see you there
going {area} late
lurking {area}
""",
"support": """
Going {area} with you
I'll support {area}
smokes for {area}
going {area}, I have flashes
{area}, I'm behind you
I'll come {area} and trade
""",
"marksman": """
Taking {area}.
Going {area} for the long angle.
I'll cover {area}.
{area}, I'll pick first.
Going {area}, scoped.
""",
}

L["round_plan_defend"] = {
"entry": """
I'll push {area}
going {area} early
taking {area} aggressive
{area}, I'll go for a pick
going {area} for one
""",
"anchor": """
I've got {area}.
Holding {area}.
I'll anchor {area}.
{area} is mine.
Sitting {area}.
Anchoring {area}, call if they rotate.
""",
"lurker": """
I'll sit {area}
going {area}
{area}, hidden
taking {area}, quiet
I'll be {area}
""",
"support": """
I'll be {area}
holding {area} with you
{area}, smoke ready
going {area}, I'll help rotate
{area}, I've got utility
""",
"marksman": """
Watching {area}.
Taking {area}, long.
{area}, scoped.
I'll hold {area}.
{area}. I have the long line.
""",
}

L["bomb_pickup"] = {
"entry": """
got the bomb
bomb on me
I have it
got it, lets go
bomb with me
""",
"anchor": """
I have the bomb.
Bomb on me.
Got the bomb.
I'll carry.
""",
"lurker": """
got the bomb
bomb on me
I have it
""",
"support": """
I have the bomb!
got the bomb, stay with me
bomb on me guys
got it, cover me
""",
"marksman": """
Bomb on me.
I have it.
Got the bomb.
""",
}

L["bomb_planting"] = {
"entry": """
planting
planting cover
planting {area}
on it, cover
planting go go
""",
"anchor": """
Planting.
Planting, cover me.
Planting at {area}.
Starting the plant.
""",
"lurker": """
planting
planting, quiet
planting {area}
""",
"support": """
Planting!
planting, cover me
planting {area}, watch my back
planting guys
""",
"marksman": """
Planting.
Planting, watch my back.
Planting at {area}.
""",
}

L["bomb_planted"] = {
"entry": """
planted
bomb down {area}
it's down
planted lets go
bomb's down
""",
"anchor": """
Bomb is down at {area}.
Planted.
Bomb's down. Play the post-plant.
Planted at {area}. Hold it.
""",
"lurker": """
planted
bomb down {area}
it's down
""",
"support": """
Planted!
bomb down {area}
it's down guys, spread out
planted, hold it
""",
"marksman": """
Planted.
Bomb down, {area}.
It's down. Watching the defuse.
""",
}

L["bomb_defusing"] = {
"entry": """
defusing
on it
defusing cover
""",
"anchor": """
Defusing.
Defusing, cover me.
On the bomb.
""",
"lurker": """
defusing
on it
""",
"support": """
Defusing!
defusing, cover me
on the bomb guys
""",
"marksman": """
Defusing.
On it.
""",
}

L["bomb_dropped"] = {
"entry": """
bomb {area}
bomb down {area}
bomb dropped {area}
someone get the bomb {area}
""",
"anchor": """
Bomb dropped at {area}.
Bomb's on the ground, {area}.
Bomb is at {area}.
""",
"lurker": """
bomb {area}
bomb dropped {area}
""",
"support": """
Bomb dropped {area}!
someone grab the bomb, {area}
bomb's at {area}
""",
"marksman": """
Bomb at {area}.
Bomb dropped, {area}.
""",
}

L["enemy_bomb_planted"] = {
"entry": """
planted {area}, retake
they planted {area}
go {area} now
retake {area}
""",
"anchor": """
They planted at {area}.
Bomb's down at {area}. Retake together.
Planted {area}. Group up first.
They planted {area}.
""",
"lurker": """
planted {area}
they planted {area}
retake {area}
""",
"support": """
They planted {area}!
retake {area}, group up
planted {area}, let's go together
bomb {area}, retake
""",
"marksman": """
Planted, {area}.
They planted {area}. I'll cover the retake.
Bomb's down {area}.
""",
}

L["flag_taken"] = {
"entry": """
got the flag
flag
I have their flag
got it, running
flag lets go
""",
"anchor": """
I have the flag.
Got their flag.
Flag's on me.
""",
"lurker": """
got the flag
flag on me
took it lol
""",
"support": """
Got the flag!
flag on me, cover me
I have it, escort me
""",
"marksman": """
Flag on me.
Got their flag.
""",
}

L["flag_lost"] = {
"entry": """
they got our flag
flag {area}
our flag, go
get our flag {area}
""",
"anchor": """
They have our flag.
Flag taken, {area}.
Our flag's gone.
""",
"lurker": """
flag gone
they took the flag
flag {area}
""",
"support": """
They took our flag!
flag carrier {area}
get our flag back
""",
"marksman": """
Flag taken.
Carrier at {area}.
They have our flag.
""",
}

L["flag_captured"] = {
"entry": """
cap!
capped
ez cap
point
""",
"anchor": """
Capture.
Capped.
That's a point.
""",
"lurker": """
cap
capped
""",
"support": """
Cap!
capped, nice
nice one, cap
""",
"marksman": """
Captured.
Point.
""",
}

L["rotate_call"] = {
"entry": """
rotate {area}
go {area}
all {area}
everyone {area}
{area} now
""",
"anchor": """
Rotate to {area}.
Rotate {area}.
They're at {area}, rotate.
Everyone to {area}.
""",
"lurker": """
rotate {area}
go {area}
they're all {area}
""",
"support": """
Rotate {area}!
rotate {area} guys
go {area}, they're there
""",
"marksman": """
Rotate, {area}.
Rotate {area}.
Go {area}.
""",
}

L["time_low"] = {
"entry": """
time
no time go
we gotta go now
time time
""",
"anchor": """
Time's short.
Running out of time.
We need to move.
Time.
""",
"lurker": """
time
no time
""",
"support": """
Time guys!
running out of time
we need to go now
""",
"marksman": """
Time.
Clock.
Little time left.
""",
}
