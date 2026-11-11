# Third pass: damage, objectives, clutch, round, orders.
L = {}

L["damage_low"] = {
"entry": """
one shot still going
low who cares
low but going
""",
"anchor": """
Very low. Covering only.
I'm one shot. Staying back.
Low. I'll hold from cover.
""",
"lurker": """
one shot lol
low
low, hiding
""",
"support": """
I'm one shot, careful
low, someone take point
very low guys
""",
"marksman": """
Low. Holding back.
One shot left.
Low. Repositioning.
""",
}

L["friendly_fire_did"] = {
"entry": """
oops sry
my bad, you walked in
sorry!
""",
"anchor": """
My fault, sorry.
Sorry. Didn't see you.
""",
"lurker": """
oops
my bad
""",
"support": """
so sorry {name}
oh no, sorry
""",
"marksman": """
My fault.
Sorry, wrong angle.
""",
}

L["friendly_fire_got"] = {
"entry": """
dude
hey watch it
""",
"anchor": """
Check fire.
Same team, {name}.
""",
"lurker": """
hey
watch it
""",
"support": """
careful, it's me!
hey, friendly
""",
"marksman": """
Friendly, check fire.
That's me.
""",
}

L["bomb_pickup"] = {
"entry": """
bomb's mine
got it go go
""",
"anchor": """
I'll take the bomb.
I have it. Stay close.
""",
"lurker": """
got it
bomb on me
""",
"support": """
got the bomb, stick with me
I'll carry it
""",
"marksman": """
Bomb on me. Escort me.
I'll carry.
""",
}

L["bomb_planting"] = {
"entry": """
planting, cover
planting now
""",
"anchor": """
Planting. Watch my back.
Planting now.
""",
"lurker": """
planting
planting dont make noise
""",
"support": """
planting! cover
planting now, watch out
""",
"marksman": """
Planting now.
Planting. Cover.
""",
}

L["bomb_planted"] = {
"entry": """
it's down lets go
planted, play it
""",
"anchor": """
Planted. Spread out.
Bomb's down. Hold your angles.
""",
"lurker": """
planted {area}
bomb down, hiding
""",
"support": """
bomb's down! hold it
planted, spread out
""",
"marksman": """
Planted. Watching it.
Bomb's down {area}. Holding.
""",
}

L["bomb_defusing"] = {
"entry": """
defusing, go
on the bomb
""",
"anchor": """
On the bomb. Cover.
Defusing now.
""",
"lurker": """
defusing quiet
on the bomb
""",
"support": """
defusing, cover!
on the bomb, help
""",
"marksman": """
Defusing now.
On the bomb.
""",
}

L["bomb_dropped"] = {
"entry": """
bomb at {area} grab it
bomb dropped go {area}
""",
"anchor": """
Bomb on the ground at {area}.
Bomb dropped {area}. Someone get it.
""",
"lurker": """
bomb at {area}
bomb on the floor {area}
""",
"support": """
bomb dropped at {area}, get it!
grab the bomb, {area}
""",
"marksman": """
Bomb is at {area}.
Bomb on the ground, {area}.
""",
}

L["enemy_bomb_planted"] = {
"entry": """
they planted {area} go go
retake {area} now
""",
"anchor": """
Bomb's down {area}. Group up.
They planted at {area}. Retake together.
""",
"lurker": """
they planted {area}
planted {area} btw
""",
"support": """
they planted {area}, retake together!
planted at {area}, let's go
""",
"marksman": """
Planted, {area}. Covering.
Retake {area}. I'll watch the long line.
""",
}

L["flag_taken"] = {
"entry": """
got the flag run
flag on me lets go
""",
"anchor": """
Flag is on me.
Have the flag. Cover me.
""",
"lurker": """
got their flag
flag
""",
"support": """
flag on me, help
I have the flag!
""",
"marksman": """
Have the flag.
Flag on me. Escort.
""",
}

L["flag_lost"] = {
"entry": """
flag gone, chase
they took our flag
""",
"anchor": """
Our flag is gone.
They have our flag. {area}.
""",
"lurker": """
flag carrier {area}
our flag's gone
""",
"support": """
our flag! get him
flag gone, {area}
""",
"marksman": """
Carrier, {area}.
Flag taken.
""",
}

L["flag_captured"] = {
"entry": """
cap lets go
capped ez
""",
"anchor": """
Point.
Good cap.
""",
"lurker": """
cap
point
""",
"support": """
capped!
nice cap
""",
"marksman": """
Cap.
Good.
""",
}

L["rotate_call"] = {
"entry": """
everyone {area} now
{area} now go
""",
"anchor": """
Rotate {area}. Now.
Everyone {area}.
""",
"lurker": """
rotate {area}
all {area}
""",
"support": """
everyone {area}!
rotate {area}, quick
""",
"marksman": """
Rotate {area}.
{area}. Rotate.
""",
}

L["time_low"] = {
"entry": """
time, go now
we gotta move
""",
"anchor": """
Time is short.
We need to go now.
""",
"lurker": """
time
running out
""",
"support": """
time guys, go!
we need to move now
""",
"marksman": """
Time.
We have to move.
""",
}

L["clutch_start"] = {
"entry": """
watch this
I got this, chill
alone, fine
""",
"anchor": """
I'm last. Quiet please.
Just me. I'll take my time.
1v{count}. Give me info.
""",
"lurker": """
my time lol
1v{count}, shh
just me, quiet
""",
"support": """
last one, I'll try
any info?
1v{count}, help me with info
""",
"marksman": """
Last one. Info only.
Just me. Slow.
1v{count}.
""",
}

L["clutch_won"] = {
"entry": """
too easy
clutch lets go
ez clap
""",
"anchor": """
Got there.
Round.
Done.
""",
"lurker": """
lol
they forgot me
ez
""",
"support": """
got them!
yes!! phew
""",
"marksman": """
Done.
Clean.
Round.
""",
}

L["clutch_lost"] = {
"entry": """
so close
argh
""",
"anchor": """
Close. Sorry.
Didn't make it.
""",
"lurker": """
damn
nt
""",
"support": """
sorry guys
so close
""",
"marksman": """
Close.
Sorry.
""",
}

L["human_clutch_cheer"] = {
"entry": """
go {name}
""",
"anchor": """
Steady, {name}.
""",
"lurker": """
gl {name}
go {name}
""",
"support": """
come on {name}!!
you can do it {name}
""",
"marksman": """
Steady, {name}.
Take your time, {name}.
""",
}

L["human_clutch_won"] = {
"entry": """
{name} insane
{name} lets go
""",
"anchor": """
Well played, {name}.
""",
"lurker": """
nice {name}
{name} lol
""",
"support": """
yes {name}!!
{name} you're a hero
""",
"marksman": """
Clean, {name}.
""",
}

L["round_lost_streak"] = {
"entry": """
come on guys
one round, let's go
""",
"anchor": """
Slow down. Together this time.
Let's play it slower.
""",
"lurker": """
they're reading us
switch it up
""",
"support": """
we got this, together
one round guys
""",
"marksman": """
Change the plan.
They know our setup.
""",
}

L["killed_by_cheap"] = {
"entry": """
really?
wow ok
come on
""",
"anchor": """
Okay then.
Hm.
""",
"lurker": """
lol ok
wow
""",
"support": """
oof
ouch
""",
"marksman": """
Lucky.
Okay.
""",
}

L["order_regroup"] = {
"entry": """
coming back
regrouping
""",
"anchor": """
Coming to you.
Regrouping.
""",
"lurker": """
coming back
on my way
""",
"support": """
coming back to you!
regrouping
""",
"marksman": """
Coming back.
On my way.
""",
}

L["order_done"] = {
"entry": """
at {area}
here
""",
"anchor": """
In position at {area}.
Set.
""",
"lurker": """
in position
here {area}
""",
"support": """
here!
in position {area}
""",
"marksman": """
At {area}.
Set at {area}.
""",
}

L["order_busy"] = {
"entry": """
fighting, wait
can't, busy
""",
"anchor": """
Busy. Wait.
Pinned. In a second.
""",
"lurker": """
cant now
wait
""",
"support": """
can't, one sec
busy, sorry
""",
"marksman": """
Engaged. Wait.
Not now.
""",
}

L["order_unclear"] = {
"entry": """
where?
what?
""",
"anchor": """
Where?
Say again.
""",
"lurker": """
what
where
""",
"support": """
where do you want me?
huh?
""",
"marksman": """
Say again.
Where?
""",
}

L["order_follow"] = {
"entry": """
behind you
lead the way
""",
"anchor": """
On you.
""",
"lurker": """
k following
ok
""",
"support": """
on you!
""",
"marksman": """
On you.
""",
}

L["order_goto"] = {
"entry": """
{area} going
""",
"anchor": """
Heading {area} now.
""",
"lurker": """
heading {area}
on my way
""",
"support": """
going now!
""",
"marksman": """
Copy, {area}.
""",
}

L["ping_help_ack"] = {
"entry": """
on my way {name}
""",
"anchor": """
Coming to you.
Hold on, {name}.
""",
"lurker": """
coming {name}
on my way
""",
"support": """
hold on {name}!
""",
"marksman": """
Coming.
Hold on.
""",
}

L["ping_cancel"] = {
"entry": """
fine
ok then
""",
"anchor": """
Understood.
Okay, back to it.
""",
"lurker": """
ok
fine
""",
"support": """
okay, back to it
sure
""",
"marksman": """
Understood.
Okay.
""",
}

L["squad_leader"] = {
"entry": """
your call {name}
lead {name}, I'm entry
""",
"anchor": """
We're with you, {name}.
Lead us, {name}.
""",
"lurker": """
ok boss
k {name}
""",
"support": """
we're with you {name}
lead us {name}!
""",
"marksman": """
Lead on.
With you, {name}.
""",
}

L["reply_thanks"] = {
"entry": """
yw
sure
""",
"anchor": """
Sure.
Of course.
""",
"lurker": """
np np
""",
"support": """
always!
yw
""",
"marksman": """
No problem.
yw
""",
}

L["reply_sorry"] = {
"entry": """
it's fine
happens
""",
"anchor": """
It happens.
Don't worry about it.
""",
"lurker": """
its ok
all good
""",
"support": """
it's ok!
happens to everyone
""",
"marksman": """
No harm.
It's fine.
""",
}

L["reply_greeting"] = {
"entry": """
hi
""",
"anchor": """
Hey.
""",
"lurker": """
yo
""",
"support": """
hello!
""",
"marksman": """
hey {name}
""",
}

L["warmup"] = {
"entry": """
ready when you are
let's get it started
""",
"anchor": """
Good luck all.
Let's play.
""",
"lurker": """
gl
ready
""",
"support": """
have fun all!
ready
""",
"marksman": """
Ready.
glhf all
""",
}
