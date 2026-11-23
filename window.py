"""The Mod Manager window: browse, search, install, update and remove community mods."""
import json
import os
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox

from . import installer as ins
from .index import data_dir, load_index, search
from .submit import issue_url, parse_repo, report_url

try:
    from tavern_shared.theme import AMBER, BG, BORDER, MUTED, PARCH, SURF, _btn, _mk_scrollbar
except Exception:  # running outside the launcher
    BG, SURF, BORDER, AMBER, PARCH, MUTED = "#1a1210", "#241c17", "#4a3828", "#e8a840", "#f0e6cc", "#8a7a62"

    def _btn(parent, text, cmd, style="normal", **kw):
        return tk.Button(parent, text=text, command=cmd, **kw)

    def _mk_scrollbar(parent, command, orient="vertical"):
        return tk.Scrollbar(parent, command=command, orient=orient)

try:
    from tavern_shared.window_chrome import _finish_dark_window, _set_window_icon, _start_hidden
except Exception:
    _finish_dark_window = _set_window_icon = _start_hidden = lambda w: None

WARNING = ("Mods run code on your PC. This list is submitted by the community and isn't reviewed, "
           "so only install mods you trust.")
NO_MELON = "Install MelonLoader first from the launcher's Mods window."
SUBMITTED = ("Your browser will open GitHub. Submit the issue there; the mod shows up here within a few "
             "minutes once its checks pass.")
BUTTON_TEXT = {"not_installed": "Install", "installed": "Installed ✓", "update": "Update",
               "unavailable": "Unavailable"}
BUTTON_STYLE = {"not_installed": "primary", "installed": "dim", "update": "success", "unavailable": "dim"}
SIDE_LABEL = {"client": "client", "server": "server", "both": "client + server"}


class ModManagerWindow(tk.Toplevel):
    def __init__(self, parent, exe_path, *, side="client", load=load_index, download=None, settings_path=None,
                 **panel_options):
        super().__init__(parent)
        _start_hidden(self)
        self.title("Mod Manager")
        self.configure(bg=BG)
        self.geometry("920x640")
        self.minsize(640, 420)
        self.side = side
        self.panel_options = panel_options
        self.panels = {}
        _set_window_icon(self)
        self.launcher = parent
        self.game_dir = os.path.dirname(exe_path)
        self._load = load
        self._download = download
        self._settings_path = settings_path or os.path.join(data_dir(), "mod_manager_settings.json")
        self.mods = None
        self.records = ins.load_records(self.game_dir)
        self.view = "browse"
        self.busy = False
        self.action_buttons = {}
        self._q = queue.Queue()
        self._build()
        _finish_dark_window(self)
        self._poll()
        self.refresh()

    # ---------- layout ----------
    def _build(self):
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=10, pady=(10, 0))
        extra = ("modpacks", "Modpacks") if self.side == "client" else ("server_pack", "Server pack")
        self.tabs = {}
        for key, label in (("browse", "Browse"), ("installed", "Installed (0)"), extra):
            b = _btn(bar, label, lambda k=key: self.show_tab(k), font=("Segoe UI", 10, "bold"), padx=14, pady=6)
            b.pack(side="left", padx=(0, 2))
            self.tabs[key] = b
        self.browse_btn, self.installed_btn = self.tabs["browse"], self.tabs["installed"]
        _btn(bar, "+ Submit a mod", self.open_submit, "primary", font=("Segoe UI", 9, "bold"),
             padx=10, pady=4).pack(side="right")
        self.update_all_btn = _btn(bar, "Update all (0)", self.update_all, "success", font=("Segoe UI", 9),
                                   padx=10, pady=4)
        self.update_all_btn.pack(side="right", padx=4)
        _btn(bar, "⟳", self.refresh, font=("Segoe UI", 9), padx=8, pady=4).pack(side="right")
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=10)

        self.status_var = tk.StringVar(value="Loading the mod list…")
        tk.Label(self, textvariable=self.status_var, bg=BG, fg=MUTED, font=("Segoe UI", 8), anchor="w"
                 ).pack(side="bottom", fill="x", padx=10, pady=(4, 8))

        self._list_area = tk.Frame(self, bg=BG)
        self._panel_area = tk.Frame(self, bg=BG)
        top = tk.Frame(self._list_area, bg=BG)
        top.pack(fill="x", pady=(8, 6))
        self.search_var = tk.StringVar()
        e = tk.Entry(top, textvariable=self.search_var, bg=SURF, fg=PARCH, insertbackground=AMBER,
                     relief="flat", font=("Segoe UI", 10), bd=6)
        e.pack(side="left", fill="x", expand=True)
        self.search_var.trace_add("write", lambda *_: self.render())
        self.side_var = tk.StringVar(value="all")
        for value, label in (("all", "All"), ("client", "Client"), ("server", "Server")):
            tk.Radiobutton(top, text=label, value=value, variable=self.side_var, command=self.render,
                           indicatoron=False, bg=SURF, fg=PARCH, selectcolor=BORDER, activebackground=BORDER,
                           activeforeground=AMBER, relief="flat", bd=0, padx=10, pady=4,
                           font=("Segoe UI", 9)).pack(side="left", padx=(6 if value == "all" else 2, 0))

        body = tk.Frame(self._list_area, bg=BG)
        body.pack(fill="both", expand=True)
        self._canvas = tk.Canvas(body, bg=BG, highlightthickness=0)
        sb = _mk_scrollbar(body, self._canvas.yview)
        sb.pack(side="right", fill="y")
        self._canvas.config(yscrollcommand=sb.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        self._list = tk.Frame(self._canvas, bg=BG)
        self._list_item = self._canvas.create_window((0, 0), window=self._list, anchor="nw")
        self._list.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(self._list_item, width=e.width))
        self.bind("<MouseWheel>", self._on_wheel, add="+")
        self._list_area.pack(fill="both", expand=True, padx=10)

    def show_tab(self, name):
        if name not in self.tabs:
            return
        self.view = name
        if name in ("browse", "installed"):
            self._panel_area.pack_forget()
            for panel in self.panels.values():
                panel.pack_forget()
            self._list_area.pack(fill="both", expand=True, padx=10)
            self.render()
        else:
            self._list_area.pack_forget()
            self._panel_area.pack(fill="both", expand=True, padx=10, pady=(6, 0))
            for key, panel in self.panels.items():
                if key != name:
                    panel.pack_forget()
            panel = self.panels.get(name) or self._make_panel(name)
            self.panels[name] = panel
            panel.pack(fill="both", expand=True)
            if hasattr(panel, "refresh"):
                panel.refresh()
        self._mark_tabs()

    def _make_panel(self, name):
        if name == "modpacks":
            from . import packhooks
            if packhooks.GUARD_MESSAGE:
                return tk.Label(self._panel_area, text=packhooks.GUARD_MESSAGE, bg=BG, fg=AMBER,
                                font=("Segoe UI", 10), wraplength=560, justify="left")
            from .modpacks.window import ModpacksPanel
            panel = ModpacksPanel(self._panel_area, self.launcher, self.game_dir)
            self.launcher._modpacks_window = panel  # Modpacks refreshes this after launches and updates
            return panel
        return self._make_server_panel()

    def _make_server_panel(self):
        return tk.Label(self._panel_area, text="Server pack", bg=BG, fg=MUTED)

    def _mark_tabs(self):
        for key, b in self.tabs.items():
            b.config(fg=AMBER if key == self.view else PARCH)

    def _on_wheel(self, event):
        if self.view not in ("browse", "installed"):
            return
        try:
            if self.winfo_exists() and str(event.widget).startswith(str(self)):
                self._canvas.yview_scroll(int(-event.delta / 120), "units")
        except tk.TclError:
            pass

    # ---------- thread plumbing ----------
    def _poll(self):
        try:
            while True:
                fn = self._q.get_nowait()
                fn()
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(30, self._poll)

    def _ui(self, fn):
        """Run fn on the Tk thread (safe to call from a worker)."""
        self._q.put(fn)

    def _run(self, work, done, label):
        self._set_busy(True, label)

        def worker():
            try:
                result, err = work(), None
            except Exception as e:  # reported to the user below
                result, err = None, e
            self._ui(lambda: (self._set_busy(False), done(result, err)))
        threading.Thread(target=worker, daemon=True).start()

    def _ask_from_worker(self, title, text):
        box, ev = {}, threading.Event()

        def ask():
            box["ok"] = messagebox.askyesno(title, text, parent=self)
            ev.set()
        self._ui(ask)
        ev.wait()
        return box["ok"]

    # ---------- data ----------
    def mod_by_id(self, mod_id):
        return next((m for m in self.mods or [] if m.id == mod_id), None)

    def refresh(self):
        def done(result, err):
            mods, note = result if result else ([], "Couldn't load the mod list.")
            self.mods = mods
            self.records = ins.load_records(self.game_dir)
            self.render()
            self.status_var.set(note or f"{len(mods)} mod{'s' if len(mods) != 1 else ''} in the community list.")
        self._run(self._load, done, "Loading the mod list…")


    def _visible(self):
        mods = search(self.mods or [], self.search_var.get(), self.side_var.get())
        if self.view == "installed":
            mods = [m for m in mods if m.id in self.records]
        return mods

    def _statuses(self):
        return {m.id: ins.status(self.records, m) for m in self.mods or []}

    # ---------- rendering ----------
    def render(self):
        for child in self._list.winfo_children():
            child.destroy()
        self.action_buttons = {}
        statuses = self._statuses()
        n_inst = sum(1 for m in self.mods or [] if m.id in self.records)
        n_upd = sum(1 for s in statuses.values() if s == "update")
        self.installed_btn.config(text=f"Installed ({n_inst})")
        self.update_all_btn.config(text=f"Update all ({n_upd})",
                                   state="normal" if n_upd and not self.busy else "disabled")
        self._mark_tabs()
        if self.view not in ("browse", "installed"):
            return
        mods = self._visible()
        if self.mods is not None and not mods:
            msg = ("No mods installed from the list yet." if self.view == "installed"
                   else "No mods match your search.")
            tk.Label(self._list, text=msg, bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=12)
        for m in mods:
            self._card(m, statuses[m.id])

    def _card(self, m, state):
        card = tk.Frame(self._list, bg=SURF, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 6))
        left = tk.Frame(card, bg=SURF)
        left.pack(side="left", fill="both", expand=True, padx=10, pady=8)
        head = tk.Frame(left, bg=SURF)
        head.pack(anchor="w", fill="x")
        tk.Label(head, text=m.name, bg=SURF, fg=AMBER, font=("Georgia", 10, "bold")).pack(side="left")
        rec = self.records.get(m.id)
        ver = m.latest_tag or "no release"
        if state == "update":
            ver = f"{rec.get('tag')} → {m.latest_tag}"
        meta = f"   {ver}   ·   {SIDE_LABEL[m.side]}   ·   by {m.author}"
        tk.Label(head, text=meta, bg=SURF, fg=MUTED, font=("Segoe UI", 8)).pack(side="left")
        if m.description:
            tk.Label(left, text=m.description, bg=SURF, fg=PARCH, font=("Segoe UI", 9), wraplength=480,
                     justify="left", anchor="w").pack(anchor="w", pady=(3, 0))

        right = tk.Frame(card, bg=SURF)
        right.pack(side="right", padx=10, pady=8)
        more = _btn(right, "⋯", None, font=("Segoe UI", 10), padx=8, pady=2)
        more.config(command=lambda b=more, mod=m: self._menu(b, mod))
        more.pack(side="right", padx=(6, 0))
        btn = _btn(right, BUTTON_TEXT[state], lambda mod=m: self._on_action(mod), BUTTON_STYLE[state],
                   font=("Segoe UI", 9, "bold"), padx=12, pady=4, width=11)
        if state in ("installed", "unavailable") or self.busy:
            btn.config(state="disabled")
        btn.pack(side="right")
        self.action_buttons[m.id] = btn

    def _menu(self, widget, m):
        menu = tk.Menu(self, tearoff=False, bg=SURF, fg=PARCH, activebackground=BORDER, activeforeground=AMBER)
        menu.add_command(label="Open GitHub page", command=lambda: webbrowser.open("https://github.com/" + m.repo))
        menu.add_command(label="Report this mod", command=lambda: webbrowser.open(report_url(m.id)))
        if self.side == "client" and m.latest_tag:
            sub = tk.Menu(menu, tearoff=False, bg=SURF, fg=PARCH, activebackground=BORDER, activeforeground=AMBER)
            for name in self.pack_names():
                sub.add_command(label=name, command=lambda n=name: self.add_to_pack(m, n))
            if self.pack_names():
                sub.add_separator()
            sub.add_command(label="New pack…", command=lambda: self._new_pack_for(m))
            menu.add_cascade(label="Add to pack", menu=sub, state="disabled" if self.busy else "normal")
        if m.id in self.records:
            menu.add_separator()
            menu.add_command(label="Uninstall", command=lambda: self.uninstall(m),
                             state="disabled" if self.busy else "normal")
        menu.tk_popup(widget.winfo_rootx(), widget.winfo_rooty() + widget.winfo_height())

    def _set_busy(self, busy, msg=None):
        self.busy = busy
        if msg:
            self.status_var.set(msg)
        if self.mods is not None:
            self.render()

    # ---------- actions ----------
    def _on_action(self, m):
        self.install(m)

    def pack_names(self):
        try:
            from .modpacks import engine
            return [p.name for p in engine.list_packs(self.game_dir)]
        except Exception:
            return []

    def _new_pack_for(self, m):
        from tkinter import simpledialog
        name = simpledialog.askstring("New pack", "Name for the new pack:", parent=self)
        if name and name.strip():
            self.add_to_pack(m, name.strip(), create=True)

    def add_to_pack(self, m, pack_name, create=False):
        if self.busy or not m.latest_tag:
            return
        from .modpacks import engine

        def work():
            pack = engine.find_pack(self.game_dir, pack_name)
            if pack is None:
                if not create:
                    raise ins.InstallError(f"there's no pack called {pack_name}")
                pack = engine.create_pack(self.game_dir, pack_name, "all")
            return ins.install_to_pack(self.game_dir, m, pack.path, self._download, self._progress(m.name),
                                       self._confirm_replace)

        def done(r, e):
            self._after_change(f"Added {m.name} to {pack_name}.", e, m.name)
            panel = self.panels.get("modpacks")
            if e is None and panel is not None and hasattr(panel, "refresh"):
                panel.refresh()
        self._run(work, done, f"Adding {m.name} to {pack_name}…")

    def _warned(self):
        try:
            with open(self._settings_path, "r", encoding="utf-8") as f:
                return bool(json.load(f).get("warned"))
        except Exception:
            return False

    def _set_warned(self):
        try:
            os.makedirs(os.path.dirname(self._settings_path) or ".", exist_ok=True)
            with open(self._settings_path, "w", encoding="utf-8") as f:
                json.dump({"warned": True}, f)
        except OSError:
            pass

    def _can_install(self):
        if self.busy:
            return False
        if not self._warned():
            if not messagebox.askokcancel("Before you install", WARNING, parent=self):
                return False
            self._set_warned()
        if not ins.melonloader_installed(self.game_dir):
            opener = getattr(self.launcher, "_open_mods", None)
            if opener and messagebox.askyesno("MelonLoader needed", NO_MELON + "\n\nOpen the Mods window now?",
                                              parent=self):
                opener()
            elif not opener:
                messagebox.showinfo("MelonLoader needed", NO_MELON, parent=self)
            return False
        return True

    def _confirm_replace(self, paths):
        names = ", ".join(p.split("/")[-1] for p in paths)
        verb = "already exists" if len(paths) == 1 else "already exist"
        return self._ask_from_worker("Replace files?", f"{names} {verb} (installed by hand). "
                                     "Replace it and let Mod Manager manage it?")

    def _progress(self, name):
        def report(done, total):
            pct = f" {done * 100 // total}%" if total else ""
            self._ui(lambda: self.status_var.set(f"Downloading {name}…{pct}"))
        return report

    def _install_one(self, m):
        return ins.install(self.game_dir, m, self._download, self._progress(m.name), self._confirm_replace)

    def _after_change(self, ok_msg, err, name):
        self.records = ins.load_records(self.game_dir)
        self.render()
        if err is None:
            self.status_var.set(ok_msg)
        elif isinstance(err, ins.InstallCancelled):
            self.status_var.set("Cancelled.")
        elif isinstance(err, ins.ModLockedError):
            self.status_var.set(str(err))
            messagebox.showwarning("Mod Manager", str(err), parent=self)
        else:
            text = f"Couldn't install {name}: {err}"
            self.status_var.set(text)
            messagebox.showerror("Mod Manager", text, parent=self)

    def install(self, m):
        if not self._can_install():
            return
        verb = "Updated" if m.id in self.records else "Installed"
        self._run(lambda: self._install_one(m),
                  lambda r, e: self._after_change(f"{verb} {m.name} {m.latest_tag}. Restart the game to load it.",
                                                  e, m.name),
                  f"Installing {m.name}…")

    def update_all(self):
        todo = [m for m in self.mods or [] if ins.status(self.records, m) == "update"]
        if not todo or not self._can_install():
            return

        def work():
            failed = []
            for m in todo:
                try:
                    self._install_one(m)
                except ins.InstallError as e:
                    failed.append((m.name, e))
                    if isinstance(e, ins.ModLockedError):
                        raise
                except Exception as e:
                    failed.append((m.name, e))
            if failed:
                raise ins.InstallError("; ".join(f"{n}: {e}" for n, e in failed))
        self._run(work, lambda r, e: self._after_change(
            f"Updated {len(todo)} mod{'s' if len(todo) != 1 else ''}. Restart the game to load them.",
            e, "some mods"), "Updating mods…")

    def uninstall(self, m, ask=True):
        if self.busy:
            return
        if ask and not messagebox.askyesno("Uninstall", f"Remove {m.name} from this game folder?", parent=self):
            return

        def done(r, e):
            if isinstance(e, ins.ModLockedError) or e is None:
                self._after_change(f"Removed {m.name}.", e, m.name)
            else:
                self._after_change("", ins.InstallError(f"couldn't remove it ({e})"), m.name)
        self._run(lambda: ins.uninstall(self.game_dir, m.id), done, f"Removing {m.name}…")

    # ---------- submit ----------
    def open_submit(self):
        SubmitDialog(self)


class SubmitDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        _start_hidden(self)
        self.title("Submit a mod")
        self.configure(bg=BG)
        self.resizable(False, False)
        _set_window_icon(self)
        self.transient(parent)
        tk.Label(self, text="Share a mod that has a GitHub release with a .dll (or a .zip with one) attached.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9), wraplength=420, justify="left"
                 ).pack(anchor="w", padx=16, pady=(14, 6))
        self.vars = {}
        for key, label in (("repo", "GitHub repo link"), ("name", "Mod name"),
                           ("description", "Short description"), ("tags", "Tags (optional, comma separated)")):
            tk.Label(self, text=label, bg=BG, fg=PARCH, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=16,
                                                                                         pady=(6, 2))
            v = self.vars[key] = tk.StringVar()
            tk.Entry(self, textvariable=v, bg=SURF, fg=PARCH, insertbackground=AMBER, relief="flat",
                     font=("Segoe UI", 10), bd=6, width=52).pack(fill="x", padx=16)
        tk.Label(self, text="Who installs it?", bg=BG, fg=PARCH, font=("Segoe UI", 9, "bold")
                 ).pack(anchor="w", padx=16, pady=(6, 2))
        self.side = tk.StringVar(value="both")
        sides = tk.Frame(self, bg=BG)
        sides.pack(anchor="w", padx=16)
        for value, label in (("client", "Players (client)"), ("server", "Server owners"), ("both", "Both")):
            tk.Radiobutton(sides, text=label, value=value, variable=self.side, bg=BG, fg=PARCH, selectcolor=SURF,
                           activebackground=BG, activeforeground=AMBER, font=("Segoe UI", 9)).pack(side="left")
        btns = tk.Frame(self, bg=BG)
        btns.pack(fill="x", padx=16, pady=14)
        _btn(btns, "Open GitHub to submit", self._submit, "primary", font=("Segoe UI", 9, "bold"), padx=12,
             pady=6).pack(side="left")
        _btn(btns, "Cancel", self.destroy, font=("Segoe UI", 9), padx=10, pady=6).pack(side="left", padx=6)
        _finish_dark_window(self)

    def _submit(self):
        repo = parse_repo(self.vars["repo"].get())
        name = self.vars["name"].get().strip()
        if not repo:
            messagebox.showinfo("Submit a mod", "Paste the mod's GitHub link, like https://github.com/You/YourMod.",
                                parent=self)
            return
        if not name:
            messagebox.showinfo("Submit a mod", "Give the mod a name.", parent=self)
            return
        webbrowser.open(issue_url(repo, name, self.vars["description"].get().strip(), self.side.get(),
                                  self.vars["tags"].get().strip()))
        messagebox.showinfo("Submit a mod", SUBMITTED, parent=self)
        self.destroy()


def open_for(launcher, side="client", tab=None):
    """Opens (or brings forward) the window for a launcher that has a v_exe path variable."""
    exe = launcher.v_exe.get().strip() if hasattr(launcher, "v_exe") else ""
    if not exe or not os.path.isfile(exe):
        messagebox.showinfo("Mod Manager", "Set the game's exe path first.", parent=launcher)
        return None
    win = getattr(launcher, "_mod_manager_win", None)
    try:
        alive = win is not None and win.winfo_exists()
    except tk.TclError:
        alive = False
    if not alive:
        win = launcher._mod_manager_win = ModManagerWindow(launcher, exe, side=side)
    else:
        win.deiconify()
        win.lift()
    if tab:
        win.show_tab(tab)
    return win


def _install_modpacks_open_hook():
    try:
        from .modpacks import window as mp_window
    except Exception:
        return
    mp_window.OPEN_HOOK = lambda root, game_dir: open_for(root, "client", "modpacks")


_install_modpacks_open_hook()
