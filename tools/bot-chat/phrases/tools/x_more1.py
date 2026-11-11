# Third pass: contact and actions, filling thinner buckets.
L = {}

L["contact_sniper"] = {
"entry": """
sniper {area} I'm rushing him
sniper {area} he can't hit moving targets lol
scoped guy {area}, going in
sniper {area}, flash him and go
he's scoped {area}, swing fast
""",
"anchor": """
Sniper on {area}. Stay behind cover.
Long rifle at {area}. Don't give him a shot.
Sniper at {area}. Use smoke to cross.
Sniper covering {area}.
Sniper at {area}. Find another way.
""",
"lurker": """
sniper {area}, he's distracted
scope {area}, I'll sneak him
sniper {area}, back turned soon
sniper {area} watching mid
sniper sitting {area} alone
""",
"support": """
sniper {area}, wait for my smoke
sniper at {area}, careful crossing
sniper {area}! don't peek it
sniper at {area}, smoke going
sniper {area}, go round
""",
"marksman": """
Sniper at {area}. I'll take him.
Their scope, {area}. Leave him to me.
Sniper {area}. Waiting for his peek.
Sniper at {area}, he's peeking the same spot.
Scope at {area}, I'm on him.
""",
}

L["enemy_rotating"] = {
"entry": """
they're all going {area}, go other side
rotating {area}, cut them off
they're running {area}
they left, push now
""",
"anchor": """
Expect them at {area} soon.
They're coming to {area}. Hold.
Rotation toward {area}. Be ready.
They're on the move, {area}.
""",
"lurker": """
they all left for {area}
rotating {area}, I'm in their spawn lol
they went {area}, other side empty
heard them rotate {area}
""",
"support": """
they're rotating {area}, get ready
rotation {area}, help them
they're going {area}, move
they're coming {area}, stack
""",
"marksman": """
Rotating toward {area}.
They're shifting to {area}.
They left, heading {area}.
Rotation, {area}. Eyes up.
""",
}

L["enemy_low"] = {
"entry": """
one shot him {area}
he's dead dead {area} go
low guy {area} I'm on it
tagged him {area}, finish
""",
"anchor": """
He's weak at {area}.
Hit him, he's at {area}.
He's low, {area}. Careful.
Low one at {area}.
""",
"lurker": """
low one at {area}
tagged {area}
he's one shot {area}
""",
"support": """
he's one shot at {area}!
tagged at {area}, finish him
low one {area} go
""",
"marksman": """
Low, {area}.
He's weak, {area}.
Body hit, {area}.
""",
}

L["enemies_left"] = {
"entry": """
{count} left come on
{count} more lets go
just {count} left
{count} left, we got this
""",
"anchor": """
{count} left. Play it safe.
They're down to {count}.
{count} left. Trade each other.
{count} left, don't rush.
""",
"lurker": """
{count} left lol
{count} more
only {count}
""",
"support": """
{count} left, together!
{count} left, careful
{count} more guys
only {count}, stay close
""",
"marksman": """
{count} left. Steady.
{count} more.
Down to {count}.
""",
}

L["last_enemy"] = {
"entry": """
last one lets go
one left, I'm going
last guy, find him
""",
"anchor": """
One left. Hold.
Last one. Don't rush.
One left. Check corners.
""",
"lurker": """
last one lol
one left, he's hiding
1 left
""",
"support": """
last one, careful
one left, together
last guy, slow
""",
"marksman": """
Last one. Patience.
One left. Holding.
Last man. Slow.
""",
}

L["grenade_incoming"] = {
"entry": """
nade move
nade lol
grenade go
""",
"anchor": """
Grenade. Back.
Nade, get out.
Nade incoming.
""",
"lurker": """
nade
grenade, move
nade nade
""",
"support": """
nade, move move
grenade incoming!
nade, get out
""",
"marksman": """
Nade. Move.
Grenade, back off.
Nade in, clear.
""",
}

L["smoke_seen"] = {
"entry": """
smoke {area} let's go through
they smoked {area}, rush it
smoke {area}, spray it
""",
"anchor": """
Smoke at {area}. Watch the sides.
Smoke on {area}. Nobody moves.
They're smoking {area}. Get ready.
""",
"lurker": """
smoke {area}
smoke {area}, they're coming soon
they smoked {area}, fake maybe
""",
"support": """
smoke at {area}!
smoke {area}, they're coming through
smoke at {area}, get ready
""",
"marksman": """
Smoke on {area}.
Smoke at {area}. Watching the edge.
They smoked {area}.
""",
}

L["kill_multi"] = {
"entry": """
two! next
got both of them
they're dropping like flies
two down push
double kill lets go
""",
"anchor": """
Two down. Still here.
Got both. Holding.
Two less.
Two down, careful.
""",
"lurker": """
two lol
2 down from the back
got both
two, still unseen
""",
"support": """
got two! push
two down!
both dead, go go
two down guys
""",
"marksman": """
Two down.
Both down.
Two. Resetting.
Got both. Moving.
""",
}

L["kill_headshot"] = {
"entry": """
head lol
tapped
headshot lets go
""",
"anchor": """
Headshot.
Got his head.
Head. Down.
""",
"lurker": """
head
tapped him
one tap
""",
"support": """
headshot!
tapped!
got the head
""",
"marksman": """
Head.
Clean.
Tapped him.
""",
}

L["flanking"] = {
"entry": """
going round {area}, keep them busy
flank {area} on my own
going behind {area}
""",
"anchor": """
Flanking via {area}. Keep them busy.
Going round through {area}.
Taking {area} to hit their side.
""",
"lurker": """
going round {area}, keep them busy
behind them soon, {area}
flanking {area}, stay loud
going {area}, they won't see me
""",
"support": """
flanking {area}, keep them busy
going round {area}
I'll come from {area}
""",
"marksman": """
Flanking through {area}.
New angle from {area}.
Going round via {area}.
""",
}

L["falling_back"] = {
"entry": """
fine, backing off
back, back
out out
too many
""",
"anchor": """
Falling back.
Pulling back to {area}.
Falling back. Regroup.
Backing off to {area}.
""",
"lurker": """
backing off
going back
out
""",
"support": """
falling back, regroup
back off guys
falling back with you
""",
"marksman": """
Falling back.
Backing off.
Pulling back to {area}.
""",
}

L["reloading"] = {
"entry": """
reloading, one sec
reloading cover me
""",
"anchor": """
Reloading. Watch my angle.
Reloading here.
""",
"lurker": """
reload
reloading quick
reloading, dont peek
""",
"support": """
reloading, watch it
reloading, one sec
""",
"marksman": """
Reloading. Watch it.
Loading.
""",
}

L["throw_frag"] = {
"entry": """
nade {area}
fragging {area}
nade out, push after
""",
"anchor": """
Grenade, {area}.
Frag going {area}.
Nade out.
""",
"lurker": """
nade {area}
frag out
nade out lol
""",
"support": """
nade {area}, push after
frag going {area}
nade out, wait for it
""",
"marksman": """
Frag, {area}.
Frag out.
Nade going.
""",
}

L["throw_smoke"] = {
"entry": """
smoking, go
smoke out go go
""",
"anchor": """
Smoke going on {area}.
Smoke out, cross now.
""",
"lurker": """
smoke
smoking {area}
""",
"support": """
smoke going, wait
smoke out, go
smoking {area}, cross now
""",
"marksman": """
Smoke.
Smoke going.
""",
}

L["throw_flash"] = {
"entry": """
flashing go go
flash, push
""",
"anchor": """
Flash going.
Flash, push now.
""",
"lurker": """
flashing
flash going
""",
"support": """
flash, look away
flashing for you, go
""",
"marksman": """
Flashing.
Flash going.
""",
}

L["need_help"] = {
"entry": """
need help {area}!
come {area} quick
""",
"anchor": """
They're pushing {area}. Need help.
Help at {area}, quick.
""",
"lurker": """
need help {area}
pinned {area}
""",
"support": """
help me at {area}!
need help at {area}
""",
"marksman": """
Need cover at {area}.
They're on me, {area}.
""",
}
