"""Installs, updates and removes mods in the game folder, and remembers which files each mod owns."""
import hashlib
import json
import os
import shutil
import tempfile
import zipfile

from .index import USER_AGENT

RECORDS_FILE = ".mod_manager.json"
ROOTS = {"mods": "Mods", "plugins": "Plugins", "userlibs": "UserLibs"}
LOCKED_MSG = "A mod file is in use. Close the game (or stop the server) and try again."


class InstallError(Exception):
    pass


class ModLockedError(InstallError):
    def __init__(self, msg=LOCKED_MSG):
        super().__init__(msg)


class InstallCancelled(InstallError):
    pass


def melonloader_installed(game_dir):
    return os.path.isdir(os.path.join(game_dir, "MelonLoader"))


def _ext(name):
    return os.path.splitext(name)[1].lower()


def pick_assets(assets):
    dlls = [a for a in assets if _ext(a.get("name", "")) == ".dll"]
    if dlls:
        return dlls
    zips = [a for a in assets if _ext(a.get("name", "")) == ".zip"]
    return zips[:1]


def _safe_parts(name):
    name = name.replace("\\", "/")
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        return None
    parts = [p for p in name.split("/") if p not in ("", ".")]
    if not parts or any(p == ".." or ":" in p for p in parts):
        return None
    return parts


def zip_targets(names):
    out = {}
    for n in names:
        if n.endswith("/"):
            continue
        parts = _safe_parts(n)
        if parts is None:
            continue
        root = next((i for i, p in enumerate(parts[:-1]) if p.lower() in ROOTS), None)
        if root is not None:
            out[n] = "/".join([ROOTS[parts[root].lower()]] + parts[root + 1:])
        elif _ext(parts[-1]) == ".dll":
            out[n] = "Mods/" + parts[-1]
    return out


def load_records(game_dir):
    try:
        with open(os.path.join(game_dir, RECORDS_FILE), "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_records(game_dir, records):
    path = os.path.join(game_dir, RECORDS_FILE)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    os.replace(tmp, path)


def _owned(records, mod_id):
    return {p.lower() for p in records.get(mod_id, {}).get("files", [])}


def conflicts(game_dir, mod_id, files):
    """Files that already exist but this mod didn't put there (hand-installed, or another mod's)."""
    owned = _owned(load_records(game_dir), mod_id)
    return [f for f in files if f.lower() not in owned and os.path.exists(os.path.join(game_dir, f))]


def status(records, mod):
    rec = records.get(mod.id)
    if rec:
        return "update" if mod.latest_tag and rec.get("tag") != mod.latest_tag else "installed"
    if mod.unavailable or not mod.latest_tag:
        return "unavailable"
    return "not_installed"


def default_download(url, dest, on_progress=None):
    """Streams a release file to dest over the bundled certificates; partial files are removed."""
    from .modpacks import tls
    total = [0]
    done = [0]

    def chunk(n):
        done[0] += n
        if on_progress:
            on_progress(done[0], total[0])
    tls.download(url, dest, tls.MAX_FILE, {"User-Agent": USER_AGENT}, 30, on_chunk=chunk,
                 on_size=lambda n: total.__setitem__(0, n))


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def _gather(tmp, assets, download, on_progress, infos=None):
    """Downloads assets; returns {relative target: (kind, source)}. Appends {name, url, sha256} to infos."""
    targets = {}
    for a in assets:
        parts = _safe_parts(a["name"])
        if parts is None or len(parts) != 1:
            raise InstallError(f"The release file name {a['name']!r} isn't safe to install.")
        local = os.path.join(tmp, parts[0])
        download(a["url"], local, on_progress)
        if infos is not None:
            infos.append({"name": parts[0], "url": a["url"], "sha256": file_sha256(local)})
        if _ext(a["name"]) == ".dll":
            targets["Mods/" + parts[0]] = ("file", local)
        else:
            try:
                with zipfile.ZipFile(local) as z:
                    for entry, rel in zip_targets(z.namelist()).items():
                        targets[rel] = ("zip", (local, entry))
            except zipfile.BadZipFile:
                raise InstallError(a["name"] + " isn't a valid zip file.")
    return targets


def _write_new(base_dir, rel, kind, src):
    dest = os.path.join(base_dir, *rel.split("/")) + ".mmnew"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if kind == "file":
        shutil.copyfile(src, dest)
    else:
        zpath, entry = src
        with zipfile.ZipFile(zpath) as z, z.open(entry) as i, open(dest, "wb") as o:
            shutil.copyfileobj(i, o)
    return dest


def install(game_dir, mod, download=None, on_progress=None, confirm=None):
    """Installs or updates `mod`. Returns the relative files written.

    confirm(paths) -> bool is asked before replacing files Mod Manager doesn't own."""
    download = download or default_download
    assets = pick_assets(mod.assets)
    if not assets:
        raise InstallError("This mod's release has no .dll or .zip file.")
    tmp = tempfile.mkdtemp(prefix="modmgr_")
    staged = []
    infos = []
    try:
        targets = _gather(tmp, assets, download, on_progress, infos)
        if not targets:
            raise InstallError("This mod's release has no .dll files in it.")
        clash = conflicts(game_dir, mod.id, sorted(targets))
        if clash and not (confirm and confirm(clash)):
            raise InstallCancelled("Install cancelled.")
        for rel in sorted(targets):
            staged.append(_write_new(game_dir, rel, *targets[rel]))
        try:
            for path in list(staged):
                os.replace(path, path[:-len(".mmnew")])
                staged.remove(path)
        except PermissionError:
            raise ModLockedError()

        records = load_records(game_dir)
        new = sorted(targets)
        keep = {p.lower() for p in new}
        stuck = []
        for old in records.get(mod.id, {}).get("files", []):
            if old.lower() in keep:
                continue
            try:
                os.remove(os.path.join(game_dir, *old.split("/")))
            except FileNotFoundError:
                pass
            except OSError:
                stuck.append(old)  # still ours; uninstall will try again
        records[mod.id] = {"tag": mod.latest_tag, "files": new + stuck, "assets": infos}
        save_records(game_dir, records)
        return new
    finally:
        for path in staged:
            try:
                os.remove(path)
            except OSError:
                pass
        shutil.rmtree(tmp, ignore_errors=True)


def _swap_in(staged):
    try:
        for path in list(staged):
            os.replace(path, path[:-len(".mmnew")])
            staged.remove(path)
    except PermissionError:
        raise ModLockedError()


def install_to_pack(game_dir, mod, pack_dir, download=None, on_progress=None, confirm=None):
    """Installs `mod` into a Modpacks pack folder. Returns the pack file names written.

    Mods/ files go into the pack; Plugins/ and UserLibs/ files still go into the game folder."""
    download = download or default_download
    assets = pick_assets(mod.assets)
    if not assets:
        raise InstallError("This mod's release has no .dll or .zip file.")
    tmp = tempfile.mkdtemp(prefix="modmgr_")
    staged = []
    infos = []
    try:
        targets = _gather(tmp, assets, download, on_progress, infos)
        pack_files = {rel.split("/")[-1]: t for rel, t in targets.items() if rel.split("/")[0] == "Mods"}
        game_files = {rel: t for rel, t in targets.items() if rel.split("/")[0] != "Mods"}
        if not pack_files:
            raise InstallError("This mod's release has no .dll files in it.")
        clash = conflicts(game_dir, mod.id, sorted(game_files))
        if clash and not (confirm and confirm(clash)):
            raise InstallCancelled("Install cancelled.")
        for name in sorted(pack_files):
            staged.append(_write_new(pack_dir, name, *pack_files[name]))
        for rel in sorted(game_files):
            staged.append(_write_new(game_dir, rel, *game_files[rel]))
        _swap_in(staged)
        path = os.path.join(pack_dir, "pack.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        mm = data.get("mod_manager") if isinstance(data.get("mod_manager"), dict) else {}
        mm[mod.id] = {"tag": mod.latest_tag, "files": sorted(pack_files), "assets": infos,
                      "game_files": sorted(game_files)}
        data["mod_manager"] = mm
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
        return sorted(pack_files)
    finally:
        for p in staged:
            try:
                os.remove(p)
            except OSError:
                pass
        shutil.rmtree(tmp, ignore_errors=True)


def uninstall(game_dir, mod_id):
    records = load_records(game_dir)
    for rel in records.get(mod_id, {}).get("files", []):
        try:
            os.remove(os.path.join(game_dir, *rel.split("/")))
        except FileNotFoundError:
            pass
        except PermissionError:
            raise ModLockedError()
    records.pop(mod_id, None)
    save_records(game_dir, records)
