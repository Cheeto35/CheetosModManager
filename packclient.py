"""Asks a server for its modpack over the launcher's login port, and reads the answer."""
import json
import re
import socket

LOGIN_PORT = 1762
GAME_PORT = 1757
SCHEME = "tavern://"
MAX_REPLY = 1 << 20
MAX_FILES = 300
_ADDR = re.compile(r"^([A-Za-z0-9.\-]+|\[[0-9A-Fa-f:]+\])(?::(\d{1,5}))?$")


def parse_address(text):
    """'host', 'host:port' or 'tavern://host:port' -> (host, game port), else None."""
    text = (text or "").strip()
    if text.lower().startswith(SCHEME):
        text = text[len(SCHEME):].rstrip("/")
    m = _ADDR.match(text)
    if not m:
        return None
    port = int(m.group(2)) if m.group(2) else GAME_PORT
    if not 0 < port < 65536:
        return None
    return m.group(1).strip("[]"), port


def link(host, port=GAME_PORT):
    return f"{SCHEME}{host}:{port}"


def query_pack(host, timeout=3.0, port=LOGIN_PORT):
    """Returns the server's reply dict, or None if it can't be reached or answers nonsense."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            s.sendall(json.dumps({"mod_manager": "pack"}).encode())
            chunks, size = [], 0
            while size <= MAX_REPLY:
                chunk = s.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
        if size > MAX_REPLY:
            return None
        data = json.loads(b"".join(chunks).decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


class PackError(Exception):
    pass


def parse_reply(reply, url, engine):
    """Reply -> (files, name, servers, listed) for a Modpacks manifest.

    Only file names are checked (so nothing lands outside the pack). Links and checksums aren't."""
    if not isinstance(reply, dict) or reply.get("status") != "ok":
        raise PackError("The server didn't answer with a modpack.")
    raw = reply.get("files")
    if not isinstance(raw, list) or len(raw) > MAX_FILES:
        raise PackError("The server's pack can't be read.")
    files, listed = [], {}
    for entry in raw:
        if not isinstance(entry, dict):
            raise PackError("The server's pack can't be read.")
        name, link_url = entry.get("filename"), entry.get("url")
        if (not isinstance(name, str) or not engine.is_dll(name) or "/" in name or "\\" in name
                or ":" in name or name in (".", "..") or engine.check_name(name.rsplit(".", 1)[0] or "x")):
            raise PackError("The server's pack has an unsafe file name: %r" % (name,))
        if not isinstance(link_url, str) or not link_url.lower().startswith(("http://", "https://")):
            raise PackError("The server's pack has no download link for %s." % name)
        if name.lower() in listed:
            raise PackError("The server's pack has %s twice." % name)
        listed[name.lower()] = name
        if engine.is_pack_managed_mod(name):
            continue
        digest = entry.get("sha256") if isinstance(entry.get("sha256"), str) else ""
        files.append({"filename": name, "sha256": digest.upper(), "url": link_url, "_server": True})
    addr = parse_address(url)
    servers = ["%s:%d" % addr] if addr else []
    name = reply.get("name") if isinstance(reply.get("name"), str) else ""
    return files, name.strip()[:60], servers, listed
