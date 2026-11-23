"""Server pack tab: pick the mods players need, save, and copy the line to share."""
import os
import tempfile
import tkinter as tk
from tkinter import messagebox
from urllib.parse import unquote, urlparse

from . import installer as ins
from . import serverpack

try:
    from tavern_shared.theme import AMBER, BG, BORDER, MUTED, PARCH, SURF, _btn
except Exception:
    BG, SURF, BORDER, AMBER, PARCH, MUTED = "#1a1210", "#241c17", "#4a3828", "#e8a840", "#f0e6cc", "#8a7a62"

    def _btn(parent, text, cmd, style="normal", **kw):
        return tk.Button(parent, text=text, command=cmd, **kw)

NO_ADDRESS = "<your server address>"
SAVED = "Saved. Players get the changes the next time they join."


def _launcher_cfg():
    try:
        from server.core.data_store import load_cfg
        return load_cfg() or {}
    except Exception:
        return {}


def _launcher_settings():
    try:
        from server.core.data_store import load_server_settings
        return load_server_settings() or {}
    except Exception:
        return {}


class ServerPackPanel(tk.Frame):
    def __init__(self, parent, window):
        super().__init__(parent, bg=BG)
        self.window = window
        opts = window.panel_options
        self.pack_path = opts.get("pack_path") or serverpack.pack_path()
        self.cfg = opts["cfg"] if "cfg" in opts else _launcher_cfg()
        self.settings = opts["server_settings"] if "server_settings" in opts else _launcher_settings()
        self.rows = []
        self.ticks = {}
        self._loaded = False
        self._build()

    # ---------- layout ----------
    def _build(self):
        tk.Label(self, text="Pick the mods players need for this server. Players who join get them through "
                 "Mod Manager automatically.", bg=BG, fg=MUTED, font=("Segoe UI", 9), wraplength=760,
                 justify="left").pack(anchor="w", pady=(4, 8))
        row = tk.Frame(self, bg=BG)
        row.pack(fill="x")
        tk.Label(row, text="Pack name", bg=BG, fg=PARCH, font=("Segoe UI", 9, "bold")).pack(side="left")
        self.name_var = tk.StringVar()
        tk.Entry(row, textvariable=self.name_var, bg=SURF, fg=PARCH, insertbackground=AMBER, relief="flat",
                 font=("Segoe UI", 10), bd=5, width=34).pack(side="left", padx=8)

        self.list_frame = tk.Frame(self, bg=SURF, highlightbackground=BORDER, highlightthickness=1)
        self.list_frame.pack(fill="both", expand=True, pady=8)

        btns = tk.Frame(self, bg=BG)
        btns.pack(fill="x")
        _btn(btns, "+ Add a mod from the list…", self.pick_from_list, font=("Segoe UI", 9), padx=10,
             pady=4).pack(side="left")
        _btn(btns, "+ Add a download link…", self._ask_link, font=("Segoe UI", 9), padx=10,
             pady=4).pack(side="left", padx=6)
        _btn(btns, "Save", self.save, "primary", font=("Segoe UI", 9, "bold"), padx=14, pady=4).pack(side="right")

        share = tk.Frame(self, bg=BG)
        share.pack(fill="x", pady=(12, 0))
        tk.Label(share, text="Share this with players:", bg=BG, fg=PARCH, font=("Segoe UI", 9, "bold")
                 ).pack(anchor="w")
        line = tk.Frame(share, bg=BG)
        line.pack(fill="x", pady=(2, 0))
        self.share_var = tk.StringVar(value=self._share_line())
        tk.Entry(line, textvariable=self.share_var, state="readonly", readonlybackground=SURF, fg=AMBER,
                 relief="flat", font=("Consolas", 10), bd=5).pack(side="left", fill="x", expand=True)
        _btn(line, "Copy", self.copy_share, font=("Segoe UI", 9), padx=10, pady=4).pack(side="left", padx=6)
        if NO_ADDRESS in self.share_var.get():
            tk.Label(share, text="Tip: set your public hostname in the launcher's server settings and it "
                     "shows up here.", bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")

    def _share_line(self):
        host = str(self.settings.get("public_hostname") or "").strip() or NO_ADDRESS
        try:
            port = int(self.cfg.get("server_port", 1757))
        except (TypeError, ValueError):
            port = 1757
        return f"Modpack: {host}:{port}  (players: Mod Manager → Modpacks → Join a server's pack)"

    # ---------- data ----------
    def refresh(self):
        if not self._loaded and self.window.mods is not None:
            self._load_rows()
        self._render()

    def _load_rows(self):
        default = serverpack.default_pack(self.window.records, self.window.mods)["files"]
        saved = serverpack.load_pack(self.pack_path)
        self.rows, self.ticks = [], {}
        if saved is None:
            for f in default:
                self._add_row(f, True)
        else:
            for f in saved["files"]:
                self._add_row(f, True)
            for f in default:
                self._add_row(f, False)
        self.name_var.set((saved or {}).get("name") or self.settings.get("name") or "My server")
        self._loaded = True

    def _add_row(self, f, ticked):
        name = f.get("filename")
        if not name or name in self.ticks:
            return False
        self.rows.append({k: f.get(k) for k in ("filename", "url", "sha256", "mod_id", "tag") if f.get(k) is not None})
        self.ticks[name] = tk.BooleanVar(self, value=ticked)
        return True

    def _render(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        if not self.rows:
            tk.Label(self.list_frame, text="No player mods yet. Install client or client + server mods, or add "
                     "one below.", bg=SURF, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=10)
            return
        names = {m.id: m.name for m in self.window.mods or []}
        for r in self.rows:
            label = names.get(r.get("mod_id"), r["filename"])
            extra = f"  ·  {r['filename']}" + (f"  ·  {r['tag']}" if r.get("tag") else "")
            tk.Checkbutton(self.list_frame, text=label + extra, variable=self.ticks[r["filename"]], bg=SURF,
                           fg=PARCH, selectcolor=BG, activebackground=SURF, activeforeground=AMBER,
                           font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=8, pady=1)

    # ---------- actions ----------
    def save(self):
        files = [r for r in self.rows if self.ticks[r["filename"]].get()]
        serverpack.save_pack({"name": self.name_var.get().strip() or "My server", "files": files}, self.pack_path)
        self.window.status_var.set(SAVED)

    def copy_share(self):
        self.clipboard_clear()
        self.clipboard_append(self.share_var.get())
        self.window.status_var.set("Copied. Paste it wherever you share your server.")

    def _ask_link(self):
        from tkinter import simpledialog
        url = simpledialog.askstring("Add a download link", "Direct download link to a .dll file:",
                                     parent=self.winfo_toplevel())
        if url and url.strip():
            self.add_link(url.strip())

    def add_link(self, url, mod_id=None, tag=None):
        """Downloads the file once (to know its checksum) and adds it to the list. False if it can't be used."""
        parsed = urlparse(url)
        name = unquote(os.path.basename(parsed.path))
        if parsed.scheme not in ("http", "https") or not name.lower().endswith(".dll") or "/" in name \
                or "\\" in name or ":" in name:
            self.window.status_var.set("That link has to point straight at a .dll file.")
            return False
        if name in self.ticks:
            self.ticks[name].set(True)
            self._render()
            return True
        download = self.window._download or ins.default_download

        def work():
            tmp = tempfile.mkdtemp(prefix="modmgr_")
            try:
                path = os.path.join(tmp, "f.dll")
                download(url, path, None)
                return ins.file_sha256(path)
            finally:
                import shutil
                shutil.rmtree(tmp, ignore_errors=True)

        def done(digest, err):
            if err is not None:
                self.window.status_var.set(f"Couldn't download {name}: {err}")
                return
            row = {"filename": name, "url": url, "sha256": digest}
            if mod_id:
                row.update(mod_id=mod_id, tag=tag)
            self._add_row(row, True)
            self._render()
            self.window.status_var.set(f"Added {name}. Save to share it.")
        self.window._run(work, done, f"Checking {name}…")
        return True

    def pick_from_list(self):
        choices = [m for m in self.window.mods or [] if m.latest_tag and
                   any(str(a.get("name", "")).lower().endswith(".dll") for a in m.assets)]
        if not choices:
            messagebox.showinfo("Server pack", "No mods in the list can be added yet.", parent=self.winfo_toplevel())
            return
        top = tk.Toplevel(self)
        top.title("Add a mod from the list")
        top.configure(bg=BG)
        top.transient(self.winfo_toplevel())
        lb = tk.Listbox(top, bg=SURF, fg=PARCH, selectbackground=BORDER, relief="flat", width=50, height=14,
                        font=("Segoe UI", 9))
        for m in sorted(choices, key=lambda m: m.name.lower()):
            lb.insert("end", f"{m.name}  ({m.latest_tag})")
        lb.pack(padx=12, pady=12, fill="both", expand=True)
        ordered = sorted(choices, key=lambda m: m.name.lower())

        def add():
            sel = lb.curselection()
            if not sel:
                return
            m = ordered[sel[0]]
            for a in m.assets:
                if str(a.get("name", "")).lower().endswith(".dll"):
                    self.add_link(a["url"], mod_id=m.id, tag=m.latest_tag)
            top.destroy()
        _btn(top, "Add", add, "primary", font=("Segoe UI", 9, "bold"), padx=14, pady=4).pack(pady=(0, 12))
