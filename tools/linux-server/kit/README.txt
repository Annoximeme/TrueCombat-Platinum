TrueCombat: Platinum - Linux dedicated server (preview)
=======================================================

A native 64-bit Linux build of the dedicated server. No Wine needed.
Works on any x86_64 distribution with glibc 2.34 or newer
(Ubuntu 22.04+, Debian 12+, Fedora 35+).

Setup
  1. ./install.sh /opt/truecombat-server
     Downloads about 700 MB of game data from the official release and
     verifies every file.
  2. Edit /opt/truecombat-server/home/tcetest/server.cfg
  3. Open UDP 27960 in your firewall.
  4. /opt/truecombat-server/start.sh
     or install truecombat-server.service to run it in the background.

Your server shows up in the in-game and launcher server lists automatically.

Running more than one server: give each its own port and config,
e.g. PORT=27961 CONFIG=second.cfg ./start.sh

Updating: download the new TrueCombat-Platinum-Linux-Server.tar.gz from
each release and run its install.sh into the same folder; your server.cfg
is kept. update-server.sh does this automatically, waiting until no players
are on the server before it restarts (see the comments at its top).
