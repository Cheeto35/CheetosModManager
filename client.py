"""Adds a Mod Manager button to the client launcher's main window."""
from client.core.addon_hooks import register_launcher_action

from .window import open_for

register_launcher_action("mod_manager", "🧩 Mod Manager", open_for)
