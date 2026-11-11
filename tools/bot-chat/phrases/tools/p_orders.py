L = {}

L["order_follow"] = {
"entry": """
on you {name}
following {name}
with you {name}
ok {name}, lead
""",
"anchor": """
Following you, {name}.
On you, {name}.
With you, {name}.
""",
"lurker": """
ok
following
k {name}
""",
"support": """
Following you {name}!
on you {name}
right behind you {name}
I'll follow, {name}
""",
"marksman": """
Following, {name}.
On you.
Behind you, {name}.
""",
}

L["order_hold"] = {
"entry": """
ok holding
holding
fine, holding
""",
"anchor": """
Holding.
Holding {area}.
Got it, holding here.
Holding here.
""",
"lurker": """
holding
ok
k
""",
"support": """
Holding here!
holding {area}
ok, holding
""",
"marksman": """
Holding.
Holding {area}.
Got it.
""",
}

L["order_push"] = {
"entry": """
pushing!
finally
going
lets go
pushing {area}
""",
"anchor": """
Pushing.
Moving up.
Pushing {area}.
""",
"lurker": """
going
ok
pushing
""",
"support": """
Pushing!
pushing with you
going {area}
""",
"marksman": """
Pushing.
Moving.
""",
}

L["order_goto"] = {
"entry": """
going {area}
on my way {area}
{area}, ok
""",
"anchor": """
Going to {area}.
Heading to {area}.
Copy, {area}.
""",
"lurker": """
ok {area}
going {area}
""",
"support": """
On my way to {area}!
going {area}
heading {area} now
""",
"marksman": """
Going to {area}.
Heading {area}.
Copy.
""",
}

L["order_regroup"] = {
"entry": """
coming
ok coming back
regrouping
""",
"anchor": """
Regrouping.
Coming to you.
On my way back.
""",
"lurker": """
coming
k
""",
"support": """
Regrouping!
coming to you
on my way
""",
"marksman": """
Regrouping.
Coming.
""",
}

L["order_done"] = {
"entry": """
here {area}
at {area}
in {area}
""",
"anchor": """
In position, {area}.
At {area}.
Set at {area}.
""",
"lurker": """
here
at {area}
""",
"support": """
I'm at {area}!
at {area}
in position {area}
""",
"marksman": """
In position, {area}.
Set.
""",
}

L["order_busy"] = {
"entry": """
fighting
busy
in a fight
wait
""",
"anchor": """
Can't, in a fight.
Pinned. Give me a second.
Not now.
Wait.
""",
"lurker": """
cant
busy
wait
""",
"support": """
can't right now, fighting
one sec
pinned, sorry
""",
"marksman": """
Busy.
Engaged.
Wait.
""",
}

L["order_unclear"] = {
"entry": """
what
?
huh
""",
"anchor": """
Say again?
Where?
""",
"lurker": """
?
""",
"support": """
what do you need?
sorry, where?
""",
"marksman": """
Repeat?
Where?
""",
}

L["ping_enemy_ack"] = {
"entry": """
on it
seen
going {area}
got it
""",
"anchor": """
Seen.
Watching {area}.
Copy, {area}.
""",
"lurker": """
k
seen
""",
"support": """
Got it!
watching {area}
seen, thanks
""",
"marksman": """
Seen.
On {area}.
Copy.
""",
}

L["ping_help_ack"] = {
"entry": """
coming {name}
on my way
coming!
""",
"anchor": """
Coming, {name}.
On my way.
""",
"lurker": """
coming
""",
"support": """
Coming {name}!
on my way {name}
I'm coming
""",
"marksman": """
Coming.
On my way, {name}.
""",
}

L["ping_cancel"] = {
"entry": """
ok
k
""",
"anchor": """
Okay.
Copy.
""",
"lurker": """
k
""",
"support": """
ok!
no problem
""",
"marksman": """
Copy.
""",
}

L["squad_leader"] = {
"entry": """
lead {name}
ok {name}
""",
"anchor": """
Your call, {name}.
Lead on, {name}.
""",
"lurker": """
ok {name}
""",
"support": """
Lead the way {name}!
ok {name}, tell us where
""",
"marksman": """
Your call, {name}.
""",
}

L["reply_thanks"] = {
"entry": """
np
ez
""",
"anchor": """
No problem.
np
""",
"lurker": """
np
""",
"support": """
np!
any time
""",
"marksman": """
np
""",
}

L["reply_greeting"] = {
"entry": """
yo
hey
sup
""",
"anchor": """
Hi.
hey
""",
"lurker": """
hi
""",
"support": """
hey!
hi {name}
""",
"marksman": """
hello
hey
""",
}

L["reply_sorry"] = {
"entry": """
np
all good
""",
"anchor": """
No worries.
All good.
""",
"lurker": """
np
""",
"support": """
no worries!
all good {name}
""",
"marksman": """
Fine.
np
""",
}
