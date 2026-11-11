L = {}

L["kill_confirm"] = {
"entry": """
got him
one down
down
dropped him
got one
{enemy} down
ez
killed {enemy}
he's dead
got him {area}
next
one less
dead
""",
"anchor": """
Got him.
One down.
He's down.
Killed one at {area}.
{enemy} down.
Got him, holding.
Down. Staying here.
Took one.
He's dead.
One down at {area}.
""",
"lurker": """
got him
one down
killed one {area}
got {enemy}
he didnt see me
got one from behind
dead
1 down
""",
"support": """
Got him!
one down
got one guys
killed {enemy}
he's down
got him, {area}
one down, keep going
got him for you
""",
"marksman": """
Got him.
One down.
Down.
Headed {enemy}.
Took him at {area}.
Clean.
He's done.
Dropped one, long.
""",
}

L["kill_multi"] = {
"entry": """
two down!
got both
2 down
double
two dead lets go
they're dropping
three down!
""",
"anchor": """
Two down.
Got two.
Both down.
Two down, still holding.
Got both of them.
""",
"lurker": """
got two
2 down
both dead
two from behind lol
got both, still hidden
""",
"support": """
Two down!
got two guys
got both!
two dead, push
two down, trade done
""",
"marksman": """
Two down.
Got both.
Two.
Two down, reset.
Double.
""",
}

L["kill_headshot"] = {
"entry": """
head
headshot
tapped him
one tap
right in the head
""",
"anchor": """
Headshot.
Tapped him.
Head.
Got the head.
""",
"lurker": """
head
tapped
headshot lol
one tap
""",
"support": """
Headshot!
got his head
tapped him
head!
""",
"marksman": """
Head.
Headshot.
Clean head.
Right where I aimed.
Tapped.
One shot.
""",
}

L["moving_to"] = {
"entry": """
going {area}
pushing {area}
I'm going {area}
{area}, on me
heading {area}
taking {area}
going {area} who's with me
moving {area}
""",
"anchor": """
Moving to {area}.
Heading to {area}.
Going {area}.
I'll cover {area}.
Moving up to {area}.
Repositioning to {area}.
""",
"lurker": """
going {area}
heading {area}
I'll go {area}
taking {area} quiet
going {area} alone
""",
"support": """
Going {area}
heading {area} with you
moving {area}
I'll come {area}
going {area}, follow me
going {area} to help
""",
"marksman": """
Moving to {area}.
Heading {area}.
Going {area} for the angle.
Taking {area}.
Repositioning, {area}.
""",
}

L["holding"] = {
"entry": """
holding {area}
watching {area}
I got {area}
{area} is mine
holding {area} for now
""",
"anchor": """
Holding {area}.
I've got {area}.
Holding {area}, nobody gets through.
{area} is covered.
Watching {area}.
I'll sit {area}.
Holding {area}. Go do your thing.
""",
"lurker": """
holding {area}
sitting {area}
watching {area}
I'm {area}
waiting {area}
""",
"support": """
Holding {area}
I got {area} covered
watching {area} for you
holding {area}, call if you need me
I'm on {area}
""",
"marksman": """
Holding {area}.
Watching {area}.
On {area}.
I have {area}.
Scoped on {area}.
Got {area} locked.
""",
}

L["flanking"] = {
"entry": """
flanking {area}
going round {area}
going behind them {area}
flank {area}
""",
"anchor": """
Flanking through {area}.
Going around via {area}.
Taking {area} to flank.
""",
"lurker": """
flanking {area}
going round
going behind, {area}
taking {area}, dont wait for me
flank {area}
I'll get behind them {area}
going {area}, quiet
lurking {area}
""",
"support": """
Flanking {area}
going round {area}
I'll flank {area}
going {area} to flank
""",
"marksman": """
Flanking via {area}.
Going around through {area}.
Taking {area}, new angle.
""",
}

L["falling_back"] = {
"entry": """
backing off
falling back
back back
out
too many, back
going back
""",
"anchor": """
Falling back.
Falling back to {area}.
Pulling back.
Going back to {area}.
Giving up the ground, falling back.
Backing off, too hot.
""",
"lurker": """
backing out
pulling back
going back {area}
out
not worth it, backing off
""",
"support": """
Falling back!
fall back
back up guys
falling back to {area}
backing off, come with me
""",
"marksman": """
Falling back.
Repositioning.
Too close, backing off.
Falling back to {area}.
Pulling back.
""",
}

L["reloading"] = {
"entry": """
reloading
reload
reloading cover
reloading quick
""",
"anchor": """
Reloading.
Reloading, cover me.
Changing mag.
Reload.
""",
"lurker": """
reloading
reload
""",
"support": """
Reloading!
reloading cover me
changing mag
reloading guys
""",
"marksman": """
Reloading.
Reload.
Cycling.
Loading up.
""",
}

L["need_help"] = {
"entry": """
help {area}
need one {area}
come {area}
need a trade {area}
help me {area}
someone {area}
""",
"anchor": """
Need help at {area}.
I need someone at {area}.
They're pushing {area}, I need support.
Can't hold {area} alone.
Help at {area}.
""",
"lurker": """
need help {area}
someone come {area}
help {area}
pinned {area}
""",
"support": """
Need help {area}!
help at {area}
someone come {area} please
pinned at {area}
need a hand {area}
""",
"marksman": """
Need someone at {area}.
Help at {area}.
They're on me at {area}.
Pinned at {area}.
""",
}

L["throw_frag"] = {
"entry": """
nade out
frag out
nading {area}
frag
eat this
""",
"anchor": """
Frag out.
Grenade out.
Frag, {area}.
Nade out.
""",
"lurker": """
nade out
frag {area}
nade
""",
"support": """
Frag out!
nade out
frag {area}
grenade out guys
""",
"marksman": """
Frag out.
Nade, {area}.
Grenade.
""",
}

L["throw_smoke"] = {
"entry": """
smoke out
smoking {area}
smoke
smoke {area} go go
""",
"anchor": """
Smoke out.
Smoking {area}.
Smoke on {area}.
Smoke.
""",
"lurker": """
smoke out
smoke {area}
""",
"support": """
Smoke out!
smoking {area}
smoke going {area}, use it
smoke {area}, cross now
smoke for you
""",
"marksman": """
Smoke out.
Smoking {area}.
Smoke on {area}.
""",
}

L["throw_flash"] = {
"entry": """
flash
flashing
flash, go
flash out
""",
"anchor": """
Flash out.
Flashing.
Flash.
""",
"lurker": """
flash
flash out
""",
"support": """
Flash out!
flashing, turn away
flash, go in
flash for you
""",
"marksman": """
Flash out.
Flash.
""",
}
