# Fourth pass: more variety for the situations that fire most often.
L = {}

L["contact_one"] = {
"entry": """
one {area}, he's peeking me
{area} one, he's alone, go go
one {area} sprinting
one {area} I can take him
one {area}, he's jumping around
one at {area}, he's mine
one coming {area}
{area}, one, wide
one {area} he's turning
""",
"anchor": """
One at {area}, holding the angle.
One moving through {area}.
One at {area}. He's coming my way.
One at {area}, I won't peek.
Got one at {area}, waiting on him.
One {area}, careful.
One {area}, he's checking corners.
One at {area}. Steady.
""",
"lurker": """
one {area} hasnt seen me yet
one {area}, he's slow
one {area}, waiting till he turns
one {area}, he walked past me lol
one at {area}, I'm watching him
one {area} looking at a wall
one in {area} standing still
one {area}, going round him
one {area}, giving him a sec
one sitting {area} for ages
""",
"support": """
one at {area}, I'll help you
one {area}, I'm right there
there's one at {area}, careful guys
one {area}, he's peeking
one at {area}, trade ready
one {area}, smoke coming if you need
one {area}, he's watching
one at {area}, wait for me
""",
"marksman": """
One at {area}, far.
One {area}. Scoped.
One at {area}, he's careless.
One crossing {area}, tracking.
One on the {area} side.
One at {area}, I'll wait for the cross.
One {area}. Clean line.
One at {area}, peeking the same spot.
One at {area}, he's exposed.
One at {area}, long line.
""",
}

L["contact_many"] = {
"entry": """
{count} {area} rushing us
{count} {area} go go go
{count} at {area}, they're loud
{count} {area} I'll take the first
{count} {area} they're coming fast
""",
"anchor": """
{count} at {area}, they're grouping up.
{count} at {area}. Ready up.
{count} moving on {area}. Hold.
{count} at {area}. Nobody peeks alone.
{count} through {area}. Help me.
""",
"lurker": """
{count} {area} all together lol
{count} in {area}, going behind
{count} at {area}, theyre committing
{count} {area} slow walking
{count} {area}, their flank is empty
{count} at {area}, wait for it
""",
"support": """
{count} at {area}, group up guys
{count} at {area}, trade each other
{count} {area}, smoke going in
{count} at {area}, everyone here
{count} {area}, flash and go
""",
"marksman": """
{count} at {area}. First one's mine.
{count}, {area}, crossing.
{count} on {area}. Watch the second one.
{count} at {area}. Steady.
{count} at {area}, bunched up.
{count} in {area}. I'll open.
""",
}

L["kill_confirm"] = {
"entry": """
got him, who's next
dead lol
he's done
one down, pushing
too easy
got one
bye
next one
""",
"anchor": """
Got him. Holding here.
One down. Reset.
He's down. Watching.
Got one.
Down. Still on the angle.
""",
"lurker": """
got one from behind
he never turned
one down quiet
got him lol
got one, moving
dropped him
""",
"support": """
got him, nice
one down guys
he's dead, go go
got one!
traded!
""",
"marksman": """
One down.
Got him. Resetting angle.
He's done.
Took one.
Head. Down.
Got him long.
""",
}

L["enemy_heard"] = {
"entry": """
they're {area} I hear them
steps {area}, going
someone running {area}
footsteps {area} lets go
""",
"anchor": """
Movement at {area}. Careful.
Steps at {area}. Holding.
Someone at {area}. Not peeking.
Sound at {area}.
""",
"lurker": """
steps {area}
someone crouch walking {area}
heard them {area}
footsteps above {area}
someone reloading {area}
door {area} btw
""",
"support": """
someone at {area}, careful
footsteps {area}!
heard someone {area}
steps {area}, watch it
""",
"marksman": """
Footsteps, {area}.
Movement, {area}.
Someone at {area}.
Steps at {area}. Watching.
""",
}

L["contact_lost"] = {
"entry": """
he's hiding {area}, going after him
lost him, he's scared
he backed off {area}
""",
"anchor": """
He backed off to {area}.
Lost him. Watch {area}.
Out of sight at {area}.
""",
"lurker": """
lost him {area}, careful
he hid {area}
he went back {area} btw
""",
"support": """
he went {area}, careful
lost him near {area}
he's hiding {area}
""",
"marksman": """
Lost him at {area}.
He's gone behind {area}.
Out of sight, {area}.
""",
}

L["damage_taken"] = {
"entry": """
hit, whatever
took damage {area}
he hit me, going
""",
"anchor": """
Hit. Still holding.
Taking fire from {area}. Staying.
I'm hit. Fine for now.
""",
"lurker": """
got hit {area}
took one, moving
hit, he knows
""",
"support": """
hit, but okay
taking fire {area}, careful
I'm hit, still up
""",
"marksman": """
Hit. Changing angle.
Took one from {area}.
Hit. Moving.
""",
}

L["teammate_down"] = {
"entry": """
{name} down, I'm going
lost {name}, trading
""",
"anchor": """
{name}'s down. Careful at {area}.
We lost {name}.
""",
"lurker": """
{name} died
rip {name}
""",
"support": """
{name} down! trade
lost {name}, careful
""",
"marksman": """
{name} is down.
Lost {name} at {area}.
""",
}

L["dead_info"] = {
"entry": """
he's low, go
sorry, unlucky
{area} one shot
""",
"anchor": """
I'm down. He's at {area}.
He's hurt. {area}.
""",
"lurker": """
sorry
{area} low
he's at {area} btw
""",
"support": """
sorry! he's at {area}
he's hurt, go
""",
"marksman": """
He's at {area}.
Low. {area}.
""",
}

L["moving_to"] = {
"entry": """
pushing {area} now
going {area}, cover me
""",
"anchor": """
Moving to {area}.
Heading {area}. Covering you.
""",
"lurker": """
going {area}
heading {area}, don't wait
""",
"support": """
heading {area} with you
going {area}, I'll back you
""",
"marksman": """
Moving to {area}.
Heading {area}.
""",
}

L["holding"] = {
"entry": """
watching {area} for a bit
holding {area}
""",
"anchor": """
I've got {area}. Go.
Holding {area}. They won't pass.
""",
"lurker": """
hiding {area}
waiting {area}
""",
"support": """
holding {area}, call me
{area} covered
""",
"marksman": """
Holding {area}. Scoped.
On {area}.
""",
}

L["round_won"] = {
"entry": """
too easy
next round
""",
"anchor": """
Nice work.
Good round, all.
""",
"lurker": """
nice
gg round
""",
"support": """
gj guys!
nice one!
""",
"marksman": """
Good round.
Clean.
""",
}

L["round_lost"] = {
"entry": """
next round
argh
""",
"anchor": """
Reset. Next one.
Unlucky round.
""",
"lurker": """
nt
oh well
""",
"support": """
nice try guys!
next one!
""",
"marksman": """
Unlucky.
Reset.
""",
}
