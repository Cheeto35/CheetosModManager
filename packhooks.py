"""Turns on the built-in Modpacks launch hooks, unless the separate Modpacks addon is also on."""
import json
import os
import subprocess

GUARD_TEXT = "The separate Modpacks addon is on. Turn it off in Addons; Mod Manager includes it now."
GUARD_MESSAGE = None
_installed = False


def _standalone_enabled():
    try:
        from client.core.addon_loader import addons_dir, _enabled_addons_file
        with open(_enabled_addons_file(), "r", encoding="utf-8") as f:
            enabled = json.load(f)
        return "modpacks" in enabled and os.path.isfile(os.path.join(addons_dir(), "modpacks", "client.py"))
    except Exception:
        return False


def install_client_hooks():
    """Returns None when the hooks are on, or the message to show when another Modpacks is active."""
    global GUARD_MESSAGE, _installed
    if not _installed and (getattr(subprocess.Popen, "_modpacks", False) or _standalone_enabled()):
        GUARD_MESSAGE = GUARD_TEXT
        return GUARD_MESSAGE
    from .modpacks import client as mp_client
    if not getattr(subprocess.Popen, "_modpacks", False):
        subprocess.Popen = mp_client._Popen
    _installed = True
    GUARD_MESSAGE = None
    return None
