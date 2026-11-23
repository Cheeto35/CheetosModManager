"""The community mod list: download it, keep a saved copy, and search it."""
import json
import os
import urllib.request
from dataclasses import dataclass, field

INDEX_URL = "https://raw.githubusercontent.com/Cheeto35/ATTModIndex/main/mods.json"
USER_AGENT = "CheetosModManager/1.0"
SIDES = ("client", "server", "both")

NOTE_STALE = "Couldn't refresh the mod list; showing the saved copy."
NOTE_NONE = "Couldn't load the mod list. Check your internet connection."


@dataclass
class Mod:
    id: str
    name: str
    repo: str
    author: str = ""
    description: str = ""
    side: str = "both"
    tags: list = field(default_factory=list)
    latest_tag: str | None = None
    assets: list = field(default_factory=list)
    unavailable: bool = False


def data_dir():
    """The launcher's data folder (where it keeps its own settings)."""
    try:
        from tavern_shared.paths import _tavern_data_dir
        return _tavern_data_dir()
    except Exception:
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "TheModdingTavern")


def _parse_one(e):
    if not isinstance(e, dict):
        return None
    try:
        id_, name, repo, side = (e[k] for k in ("id", "name", "repo", "side"))
    except KeyError:
        return None
    if not all(isinstance(v, str) and v for v in (id_, name, repo)) or side not in SIDES:
        return None
    latest = e.get("latest") if isinstance(e.get("latest"), dict) else {}
    assets = [a for a in latest.get("assets") or [] if isinstance(a, dict) and a.get("name") and a.get("url")]
    tags = [str(t) for t in e.get("tags") or [] if isinstance(t, (str, int))]
    return Mod(id=id_, name=name, repo=repo, author=str(e.get("author") or repo.split("/")[0]),
               description=str(e.get("description") or ""), side=side, tags=tags,
               latest_tag=latest.get("tag") or None, assets=assets, unavailable=bool(e.get("unavailable")))


def parse_index(data):
    if not isinstance(data, list):
        return []
    return [m for m in map(_parse_one, data) if m is not None]


def search(mods, text="", side="all"):
    words = text.lower().split()
    out = []
    for m in mods:
        if side in ("client", "server") and m.side not in (side, "both"):
            continue
        hay = " ".join([m.name, m.description, m.author] + m.tags).lower()
        if all(w in hay for w in words):
            out.append(m)
    return sorted(out, key=lambda m: m.name.lower())


def _default_fetch():
    src = os.environ.get("MOD_MANAGER_INDEX") or INDEX_URL
    if not src.lower().startswith(("http://", "https://")):
        with open(src, "r", encoding="utf-8") as f:
            return f.read()
    req = urllib.request.Request(src, headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8")


def default_cache_path():
    return os.path.join(data_dir(), "mod_manager_index_cache.json")


def _read_cache(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    return data if isinstance(data, list) else None


def _write_cache(path, data):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except OSError:
        pass


def load_index(fetch=None, cache_path=None):
    """Returns (mods, note). note is None when the fresh list loaded."""
    fetch = fetch or _default_fetch
    cache_path = cache_path or default_cache_path()
    try:
        data = json.loads(fetch())
        if not isinstance(data, list):
            raise ValueError("index is not a list")
    except Exception:
        cached = _read_cache(cache_path)
        if cached is None:
            return [], NOTE_NONE
        return parse_index(cached), NOTE_STALE
    _write_cache(cache_path, data)
    return parse_index(data), None
