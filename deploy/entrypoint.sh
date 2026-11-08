#!/bin/sh
# Run Triage as PUID:PGID, like the *arr images.
#
# - PUID/PGID unset: runs as root.
# - Compose `user:` / `docker run --user`: already not root, nothing to do.
# - UMASK (optional, e.g. 002) applies to the files Triage writes.
set -e

if [ -n "$UMASK" ]; then
    umask "$UMASK"
fi

if [ "$(id -u)" != "0" ] || [ -z "$PUID$PGID" ]; then
    exec "$@"
fi

PUID=${PUID:-0}
PGID=${PGID:-0}
if [ "$PUID" = "0" ] && [ "$PGID" = "0" ]; then
    exec "$@"
fi

if ! getent group "$PGID" >/dev/null; then
    groupadd -o -g "$PGID" triage
fi
if ! getent passwd "$PUID" >/dev/null; then
    useradd -o -u "$PUID" -g "$PGID" -d /config -M -s /usr/sbin/nologin triage
fi

# /config holds the database Triage writes at every start; files left by a run as root are
# taken over too.
mkdir -p /config
if [ -n "$(find /config \( ! -user "$PUID" -o ! -group "$PGID" \) -print -quit)" ]; then
    chown -R "$PUID:$PGID" /config
fi

echo "Triage runs as uid=$PUID gid=$PGID"
exec setpriv --reuid="$PUID" --regid="$PGID" --init-groups "$@"
