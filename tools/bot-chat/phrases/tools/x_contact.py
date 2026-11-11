# Extra variants for the most frequent situations (merged into the main bank).
L = {}

L["contact_one"] = {
"entry": """
one {area} he's mine
{area} one, swinging now
yo one at {area}
one {area} I'm on him
he's {area}, going
there's one {area}
one guy {area} pushing him
1 {area} on him now
one {area}!!
contact one {area} going in
one {area}, cover me I'm peeking
one at {area} he's reloading
one {area} he's alone, go
one {area}, taking the fight
eyes on one {area}
one at {area}, wide swing
{area} has one
one {area} rushing him
saw one {area} lets go
one {area} hes looking away
""",
"anchor": """
One enemy at {area}.
Contact {area}. One.
One at {area}, he's peeking.
I have one at {area}.
One {area}. I'm staying on the angle.
One at {area}, not chasing.
One showing at {area}, holding.
One at {area}, he's careful.
One at {area}. I'll keep him there.
Enemy at {area}, one.
I see one {area}, he's looking for a gap.
One at {area}, behind cover.
One at {area}, call if he moves.
One {area}, slow walking.
Single at {area}, holding him off.
One at {area}, crouched.
One {area}. Don't push it.
One at {area}, he wants to cross.
Contact at {area}, one, I'm on it.
One at {area}, eyes on.
""",
"lurker": """
one {area} he's alone
1 at {area}
one {area}, ignoring him for now
one sitting {area} lol
there's one {area} btw
one {area} looking the other way
one {area}, I'm right behind
1 {area} hasnt moved
one {area} crouched
one {area} he's camping
one {area}, I could take him
one at {area}, waiting
guy at {area} btw
one in {area} watching mid
one {area} reloading lol
1 {area} slow walking
one {area}, he's bored
someone at {area}
one {area}, leaving him
1 {area} backwards
""",
"support": """
one at {area}, careful
one {area}, I've got your back
there's one at {area}!
one at {area}, I'll flash him
one {area}, anyone close?
one guy {area} guys
watch {area}, one there
one at {area}, don't peek alone
one at {area}, he's alone
one {area}, I'm coming
one {area}, smoke?
one at {area}, I'll trade you
one at {area}, careful he's holding
heads up {area}, one
one at {area}, looking at us
one {area}, careful going through
one {area}, I'll help
one at {area} hiding
saw one {area}
one {area}, watch the corner
""",
"marksman": """
One, {area}. Long.
One at {area}. I have the line.
One crossing {area}.
One {area}. Holding the angle.
One at {area}, he's peeking wide.
One {area}, scoped on him.
One at {area}, behind the edge.
One {area}. Distance, he can't see me.
Spotted one, {area}.
One at {area}, waiting for him to move.
One {area}. Head's showing.
One at {area}. Watching.
One on {area}, slow mover.
One at {area}, I'll take the shot.
One {area}, from the window.
One at {area}, behind the box.
One, {area}, my side.
One at {area}, he's careless.
One {area}. Patience.
One at {area}, peek timing is predictable.
""",
}

L["contact_many"] = {
"entry": """
{count} {area} lets fight
{count} at {area} send it
{count} {area} on me
{count} {area}, swing together
{count} at {area} they're rushing
{count} {area} I'm going
{count} {area} need a trade
{count} at {area} hit them now
{count} {area} they're bunched
{count} pushing {area} fight them
{count} at {area}! go go
{count} {area} with me
{count} at {area}, take them
{count} {area}, they're slow
{count} {area} entry now
""",
"anchor": """
{count} at {area}. Everyone hold.
{count} at {area}, they're coming slow.
{count} in {area}. Need help here.
{count} at {area}, I'll hold the first.
Contact {area}, {count} enemies.
{count} pushing {area}. Stack up.
{count} at {area}. Don't swing alone.
{count} at {area}, can't hold alone.
{count} in {area}, they're waiting.
{count} at {area}. Ready.
{count} through {area}, call it.
{count} at {area}. Hold your angles.
{count} at {area}, keep them out.
{count} in {area}. Everyone to {area}.
{count} at {area}, it's the push.
""",
"lurker": """
{count} {area} lol
{count} at {area}, they're all there
{count} going {area}, I'm behind
{count} in {area} btw
{count} at {area}, their back is open
{count} {area}, waiting for the push
{count} {area} slow
{count} {area}, they're talking loud
{count} {area} rushing
{count} at {area}, hitting the last one
{count} {area}, theyre not checking
{count} in {area}, all looking front
{count} {area} theyre waiting
{count} in {area} fyi
{count} at {area}, give me 5 sec
""",
"support": """
{count} at {area}, stack up
{count} {area}, smoke going
{count} at {area}! careful
{count} at {area}, need trades
{count} {area}, everyone come
{count} at {area}, help!
{count} at {area}, don't peek one by one
{count} {area}, I'll flash
{count} in {area}, group with me
{count} at {area} guys, it's the push
{count} at {area}, hold together
{count} at {area}, utility ready
{count} {area}, rotate here
{count} at {area}, I'm here with you
{count} in {area}, careful
""",
"marksman": """
{count} at {area}, long range.
{count}, {area}. I'll open.
{count} at {area}, taking the first.
{count} moving at {area}.
{count} at {area}, they're stacked.
{count} on {area}. Holding the line.
{count} crossing {area}.
{count} at {area}, give me the shot.
{count} in {area}, slow.
{count} at {area}. Scoped.
{count} at {area}, spaced out.
{count} at {area}, one peeking.
{count} on {area}, watch the second.
{count} at {area}, eyes on all.
{count}, {area}, they're careful.
""",
}

L["contact_lost"] = {
"entry": """
he's gone {area}
lost him going after
where is he
he ran off {area}
lost him {area} he's scared
lost him, pushing {area}
he hid {area}
he went back {area} chasing
""",
"anchor": """
Lost him. {area}.
He's out of sight at {area}.
Lost him near {area}, staying.
He went back into {area}.
Can't see him, {area}.
Last known {area}.
Lost him, careful at {area}.
""",
"lurker": """
lost him near {area}
he's hiding {area} somewhere
lost him, careful {area}
he went back
lost track {area}
he ducked {area}
""",
"support": """
lost him at {area}, careful
he's somewhere {area}
lost him, watch {area}
he ran {area}
can't see him, {area}
lost him {area}, he's hurt
""",
"marksman": """
Lost the line, {area}.
He's behind {area}.
Can't see him. {area}.
Gone, {area}.
He left the angle, {area}.
Last position {area}.
""",
}

L["enemy_heard"] = {
"entry": """
running {area} lets go
I hear {area} going
steps {area} someone coming
loud {area}
footsteps {area} he's close
""",
"anchor": """
Footsteps {area}. Holding.
Hearing someone near {area}.
Movement close, {area}.
Someone moving at {area}.
Hear a reload, {area}.
""",
"lurker": """
heard steps {area}
someone running {area}
reload {area} btw
heard a door {area}
steps above {area}
someone {area} close
""",
"support": """
steps at {area} guys
heard someone {area}
someone close {area}
reload {area}, push maybe
footsteps {area}, watch it
""",
"marksman": """
Footsteps, {area}.
Hearing {area}.
Movement near {area}.
Reload heard, {area}.
Door, {area}.
""",
}

L["area_clear"] = {
"entry": """
{area} clear go
{area} empty lets go
nothing {area} pushing
clear {area}, next
""",
"anchor": """
Clear at {area}.
{area} is empty.
Nothing at {area}, staying.
{area} checked.
""",
"lurker": """
{area} empty
nobody {area} lol
{area} nothing
{area} clear, odd
""",
"support": """
clear at {area}
{area} empty, come
checked {area}, clear
{area} clear, go
""",
"marksman": """
{area} clear.
Nothing at {area}.
{area} quiet.
Checked {area}.
""",
}
