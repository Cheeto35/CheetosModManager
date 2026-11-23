"""Adds a Mod Manager button to the server launcher's header, and shares the server's modpack with players."""
from server.core.auth_service import register_auth_handler
from server.core.header_registry import register_header_button
from server.core.launcher_window import ServerLauncher

from . import serverpack
from .window import open_for


def _open_mod_manager(self):
    open_for(self, "server")


ServerLauncher._open_mod_manager = _open_mod_manager
register_header_button("mod_manager", "\U0001F9E9 Mod Manager", "_open_mod_manager")
register_auth_handler(serverpack.matches, serverpack.handle)
