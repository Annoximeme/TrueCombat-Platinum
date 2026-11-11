L = {}

L["clutch_start"] = {
"entry": """
I got this
1v{count} lets go
just me
leave it to me
1v{count}, watch this
ok
""",
"anchor": """
Last one. Quiet please.
1v{count}. Give me info only.
Just me. Playing it slow.
I'm alone. Going for time.
On my own. Stay quiet.
""",
"lurker": """
quiet pls
1v{count}
just me
dont talk
ok shh
""",
"support": """
I'm last, give me info
1v{count}, any info?
just me, tell me what you saw
last one, I'll try
""",
"marksman": """
1v{count}.
Last one. Info only.
Quiet.
Alone. Patience.
""",
}

L["clutch_won"] = {
"entry": """
ez
told you
yesss
too easy
lets go
clutched
""",
"anchor": """
Got it.
Done.
That's the round.
Close one.
Took my time.
""",
"lurker": """
lol
they never checked
ez
heh
""",
"support": """
yes!
got them!
phew
close one guys
""",
"marksman": """
Done.
Round.
Patience pays.
Clean.
""",
}

L["clutch_lost"] = {
"entry": """
nearly
so close
argh
sorry
next one
""",
"anchor": """
Sorry, couldn't hold it.
Close. Sorry.
Not enough time.
Sorry team.
""",
"lurker": """
nt me
almost
damn
sry
""",
"support": """
sorry guys
so close, sorry
nt me
almost had it
""",
"marksman": """
Missed it. Sorry.
Close.
Sorry.
Not this time.
""",
}

L["human_clutch_cheer"] = {
"entry": """
come on {name}
you got this {name}
go {name}
""",
"anchor": """
Take your time, {name}.
Stay calm, {name}.
Slow, {name}. Use the clock.
""",
"lurker": """
gl {name}
you got it {name}
""",
"support": """
You got this {name}!
gl {name}
come on {name}!
believe {name}
""",
"marksman": """
Patience, {name}.
Good luck, {name}.
""",
}

L["human_clutch_won"] = {
"entry": """
{name}!!
what a clutch
{name} carry
insane {name}
""",
"anchor": """
Well played, {name}.
Good clutch, {name}.
Nice, {name}.
""",
"lurker": """
nice {name}
wp {name}
""",
"support": """
{name}!! nice!
wp {name}
great clutch {name}
""",
"marksman": """
Clean, {name}.
Well played.
Nice work, {name}.
""",
}

L["round_won"] = {
"entry": """
ez
lets go
gg round
yes
nice
easy
more
""",
"anchor": """
Good round.
Nice round.
Well played.
Good work.
That's one.
""",
"lurker": """
nice
ez
gj
""",
"support": """
Nice round guys!
gj all
nice one team
good round
wp
""",
"marksman": """
Round.
Good round.
Clean round.
""",
}

L["round_lost"] = {
"entry": """
nt
next
unlucky
argh
next one
""",
"anchor": """
Nice try.
Reset.
Next round.
Unlucky. Same plan, tighter.
""",
"lurker": """
nt
unlucky
oh well
""",
"support": """
nt guys
nice try
next one, we got this
unlucky
""",
"marksman": """
Nice try.
Next.
Reset.
""",
}

L["round_lost_streak"] = {
"entry": """
come on
we need a round
wake up
let's just go fast this time
""",
"anchor": """
Let's slow it down.
Reset. Play together.
Stick together this round.
Let's try something else.
""",
"lurker": """
switch it up
they know our spots
try other side
""",
"support": """
Let's stick together this time
come on guys, one round
we got this, together this time
let's try something different
""",
"marksman": """
Different approach.
Let's change it up.
They're reading us. Switch.
""",
}

L["match_won"] = {
"entry": """
gg
gg ez
ggs
gg wp
gg nice
""",
"anchor": """
gg
Good game.
gg wp
gg all
""",
"lurker": """
gg
ggs
""",
"support": """
gg all!
ggs, well played
gg wp everyone
gg
""",
"marksman": """
gg
Good game.
gg wp
""",
}

L["match_lost"] = {
"entry": """
gg
ggs
gg wp
""",
"anchor": """
gg
Good game.
gg wp
gg, well played
""",
"lurker": """
gg
gg wp
""",
"support": """
gg all, well played
ggs
gg wp
""",
"marksman": """
gg
gg wp
Good game.
""",
}

L["warmup"] = {
"entry": """
lets go
start already
come on
ready
anyone wanna 1v1 lol
""",
"anchor": """
Ready.
Waiting.
Ready when you are.
""",
"lurker": """
hi
ready
""",
"support": """
hey all
glhf
glhf everyone
ready
""",
"marksman": """
Ready.
glhf
""",
}

L["player_joined"] = {
"entry": """
hey {name}
yo {name}
sup {name}
""",
"anchor": """
Hi {name}.
Welcome, {name}.
hey {name}
""",
"lurker": """
hi
hey
""",
"support": """
hey {name}!
welcome {name}
hi {name}, glhf
""",
"marksman": """
Hello, {name}.
hey
""",
}

L["nice_shot_teammate"] = {
"entry": """
nice {name}
{name}!
sick
nice one
""",
"anchor": """
Nice shot, {name}.
Good kill.
Nice, {name}.
""",
"lurker": """
nice
nice {name}
""",
"support": """
nice shot {name}!
great kill {name}
nice {name}!
""",
"marksman": """
Nice shot.
Clean, {name}.
""",
}

L["killed_by_good"] = {
"entry": """
nice shot
ugh
how
ok nice
""",
"anchor": """
Nice shot.
Good shot.
Fair.
""",
"lurker": """
ns
nice
""",
"support": """
nice shot
ns
good shot {enemy}
""",
"marksman": """
Good shot.
Nice.
ns
""",
}

L["killed_by_cheap"] = {
"entry": """
really
lol
come on
""",
"anchor": """
Hm.
Okay.
""",
"lurker": """
lol
""",
"support": """
ouch
oof
""",
"marksman": """
Lucky.
Hm.
""",
}
