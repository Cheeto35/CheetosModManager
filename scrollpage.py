"""A page that scrolls when its content is taller than the window.

Tk stops reporting size changes for a canvas window that's scrolled out of view, so a list that shrinks while
you're scrolled down (a search, a tab change) used to leave a blank page with a stale scrollbar. This page
re-measures itself after every redraw and a few times a second while it's showing, instead of trusting
<Configure> events.
"""
import tkinter as tk

try:
    from tavern_shared.theme import _mk_scrollbar
except Exception:  # running outside the launcher
    def _mk_scrollbar(parent, command, orient="vertical"):
        return tk.Scrollbar(parent, command=command, orient=orient)

TICK_MS = 400


class ScrollPage(tk.Frame):
    def __init__(self, parent, bg):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = _mk_scrollbar(self, self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._item = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self._size = None
        self.canvas.bind("<Configure>", lambda e: self.sync())
        self.inner.bind("<Configure>", lambda e: self.sync())
        self.after(TICK_MS, self._tick)

    def sync(self, top=False):
        """Fit the scroll area to the content: as tall as the content, never shorter than the page (so content
        that fills the page can expand into it). top=True goes back to the top, e.g. after a new search."""
        try:
            width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
            wanted = self.inner.winfo_reqheight()
        except tk.TclError:
            return
        size = (width, max(wanted, height))
        if size != self._size:
            self._size = size
            self.canvas.itemconfigure(self._item, width=width, height=size[1])
            self.canvas.configure(scrollregion=(0, 0, width, size[1]))
        if top or wanted <= height:
            self.canvas.yview_moveto(0)

    def scrollable(self):
        try:
            return self.inner.winfo_reqheight() > self.canvas.winfo_height()
        except tk.TclError:
            return False

    def scroll(self, delta):
        if self.scrollable():
            self.canvas.yview_scroll(int(-delta / 120) or (-1 if delta > 0 else 1), "units")

    def _tick(self):
        try:
            if self.winfo_ismapped():
                self.sync()
            self.after(TICK_MS, self._tick)
        except tk.TclError:
            pass  # destroyed
