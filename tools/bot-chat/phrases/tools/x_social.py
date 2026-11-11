# Extra variants for round, match, social and order replies.
L = {}

L["round_won"] = {
"entry": """
easy round
lets go!
one more
ez ez
again
we're rolling
nice nice
""",
"anchor": """
Good round all.
Well done.
Nice. Same again.
Solid round.
Good. Keep it up.
""",
"lurker": """
gj
nice round
ez
heh
""",
"support": """
nice!! gj
great round guys
wp team
gj everyone
nice teamwork
""",
"marksman": """
Nice.
Well played.
Good round.
That works.
""",
}

L["round_lost"] = {
"entry": """
damn
argh next
close
unlucky guys
next one ours
""",
"anchor": """
Next one.
We'll get the next one.
Unlucky.
Close round.
""",
"lurker": """
nt guys
meh
unlucky
nt
""",
"support": """
nt nt
nice try all
close, next one
unlucky, we got the next
""",
"marksman": """
Close.
Unlucky.
Next.
Nice try.
""",
}

L["warmup"] = {
"entry": """
can we start
waiting for more?
lets play
gl
come on start
""",
"anchor": """
glhf
Ready here.
Waiting on players.
""",
"lurker": """
glhf
o/
""",
"support": """
hi everyone!
glhf all
good luck have fun
hi guys
""",
"marksman": """
gl
Ready when everyone is.
""",
}

L["match_won"] = {
"entry": """
gg!
gg wp all
""",
"anchor": """
gg, good game all
Good game everyone.
""",
"lurker": """
gg wp
gg all
""",
"support": """
gg everyone!
gg, thanks all
""",
"marksman": """
gg all
Well played.
""",
}

L["match_lost"] = {
"entry": """
gg, next time
gg wp
""",
"anchor": """
gg all
Good game, well played.
""",
"lurker": """
gg all
ggs
""",
"support": """
gg everyone, wp
ggs all!
""",
"marksman": """
gg all
Good game. Well played.
""",
}

L["killed_by_good"] = {
"entry": """
nice
ns
ok fair
wow
""",
"anchor": """
Nice shot.
Well played.
ns
""",
"lurker": """
nice
how
""",
"support": """
nice one
ns {enemy}
good shot!
""",
"marksman": """
Good shot.
ns
Nice angle.
""",
}

L["nice_shot_teammate"] = {
"entry": """
nice!
{name} nice
gj {name}
""",
"anchor": """
Good shot, {name}.
Nice.
""",
"lurker": """
nice
ns {name}
""",
"support": """
gj {name}!
nice one {name}!
ns {name}
""",
"marksman": """
Nice.
Good shot.
""",
}

L["player_joined"] = {
"entry": """
hi {name}
{name}!
""",
"anchor": """
hey
Hi {name}, welcome.
""",
"lurker": """
o/
hey {name}
""",
"support": """
hey {name}, welcome!
hi!
""",
"marksman": """
Hi.
welcome {name}
""",
}

L["order_hold"] = {
"entry": """
fine
holding here
ok ok holding
""",
"anchor": """
Copy, holding.
I'll hold.
Holding position.
""",
"lurker": """
holding here
ok holding
""",
"support": """
holding here for you
got it, holding
""",
"marksman": """
Holding.
Copy.
""",
}

L["order_follow"] = {
"entry": """
on you
lead
""",
"anchor": """
Behind you, {name}.
Following.
""",
"lurker": """
following you
""",
"support": """
behind you!
following {name}
""",
"marksman": """
Following.
""",
}

L["order_goto"] = {
"entry": """
going {area}
{area} on my way
""",
"anchor": """
On my way to {area}.
Heading {area}.
""",
"lurker": """
going {area}
""",
"support": """
going {area}!
on my way {area}
""",
"marksman": """
Going {area}.
""",
}

L["order_push"] = {
"entry": """
yes pushing
about time
going in
""",
"anchor": """
Pushing now.
Moving.
""",
"lurker": """
going in
""",
"support": """
going with you!
pushing now
""",
"marksman": """
Pushing now.
""",
}

L["ping_enemy_ack"] = {
"entry": """
seen going
got it {area}
""",
"anchor": """
Got it, {area}.
Watching it.
""",
"lurker": """
ok {area}
""",
"support": """
thanks, watching {area}
got it {area}
""",
"marksman": """
Watching {area}.
Got it.
""",
}

L["reply_thanks"] = {
"entry": """
np np
""",
"anchor": """
Any time.
""",
"lurker": """
np
yw
""",
"support": """
np, any time
you too!
""",
"marksman": """
Sure.
""",
}

L["reply_greeting"] = {
"entry": """
yo yo
hey hey
""",
"anchor": """
Hello.
Hi there.
""",
"lurker": """
hey
o/
""",
"support": """
hey there!
hi hi
""",
"marksman": """
Hi.
""",
}
