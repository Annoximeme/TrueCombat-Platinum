# TrueCombat: Platinum community server in a container.
#   docker compose up -d        (see compose.yaml)
# The image holds only the server binaries (a few MB). The game data (~700 MB) is
# downloaded from the official release into the /data volume on the first start and
# verified file by file, so updating the image never re-downloads unchanged paks.
FROM debian:12-slim
ARG KIT_URL=https://github.com/Annoximeme/TrueCombat-Platinum/releases/latest/download/TrueCombat-Platinum-Linux-Server.tar.gz
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl python3 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --system --uid 27960 --home-dir /data --shell /usr/sbin/nologin truecombat \
 && mkdir -p /opt/kit /data && chown truecombat /data
# A kit folder next to the Dockerfile wins over the download (local builds and CI)
COPY kit* /opt/kit-local/
RUN if [ -x /opt/kit-local/install.sh ]; then cp -a /opt/kit-local/. /opt/kit/; \
    else curl -fsSL "$KIT_URL" | tar -xz -C /opt/kit --strip-components=1; fi \
 && rm -rf /opt/kit-local && test -x /opt/kit/server/platinum-server.x86_64
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
USER truecombat
VOLUME /data
EXPOSE 27960/udp
HEALTHCHECK --interval=60s --timeout=5s --start-period=600s CMD python3 -c "import socket,os;s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(3);s.sendto(b'\xff\xff\xff\xffgetinfo hc',('127.0.0.1',int(os.environ.get('PORT','27960'))));s.recv(2048)"
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
