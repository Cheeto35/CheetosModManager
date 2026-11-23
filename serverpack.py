"""The server's modpack: which mods players need. Shared with players over the launcher's login port."""
import json
import os

from .index import data_dir

PACK_FILE = "mod_manager_server_pack.json"
PLAYER_SIDES = ("client", "both")


def pack_path():
    return os.path.join(data_dir(), PACK_FILE)


def default_pack(records, mods, name="My server"):
    """Every installed community mod that players need too, with the exact files the server has."""
    by_id = {m.id: m for m in mods}
    files = []
    for mod_id in sorted(records):
        m = by_id.get(mod_id)
        if m is None or m.side not in PLAYER_SIDES:
            continue
        for a in records[mod_id].get("assets") or []:
            if str(a.get("name", "")).lower().endswith(".dll"):
                files.append({"filename": a["name"], "url": a["url"], "sha256": a.get("sha256", ""),
                              "mod_id": mod_id, "tag": records[mod_id].get("tag")})
    return {"name": name, "files": files}


def load_pack(path=None):
    try:
        with open(path or pack_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        return None
    return {"name": str(data.get("name") or ""), "files": [f for f in data["files"] if isinstance(f, dict)]}


def save_pack(pack, path=None):
    path = path or pack_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2)
    os.replace(tmp, path)


def reply(pack):
    if not pack or not pack.get("files"):
        return {"status": "none"}
    return {"status": "ok", "name": pack.get("name") or "", "files": pack["files"]}


def matches(req):
    return isinstance(req, dict) and req.get("mod_manager") == "pack"


def handle(conn, req, ip, log_fn):
    """Login-port handler: answers {"mod_manager": "pack"} with the saved pack."""
    conn.sendall(json.dumps(reply(load_pack(pack_path()))).encode())
