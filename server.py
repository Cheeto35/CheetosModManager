"""Adds a Mod Manager button to the server launcher's header."""
from server.core.header_registry import register_header_button
from server.core.launcher_window import ServerLauncher

from .window import open_for


def _open_mod_manager(self):
    open_for(self, "server")


ServerLauncher._open_mod_manager = _open_mod_manager
register_header_button("mod_manager", "🧩 Mod Manager", "_open_mod_manager")
