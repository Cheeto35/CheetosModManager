"""Adds a Mod Manager button to the client launcher's main window, and turns on built-in Modpacks."""
from client.core.addon_hooks import register_launcher_action

from . import packhooks
from .window import open_for

packhooks.install_client_hooks()
register_launcher_action("mod_manager", "\U0001F9E9 Mod Manager", lambda launcher: open_for(launcher, "client"))
