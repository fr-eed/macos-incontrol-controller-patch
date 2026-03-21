#!/usr/bin/env python3
"""
Steam Input Controller Patch for InControl Games - GUI
"""

import subprocess
from pathlib import Path
from tkinter import Tk, Label, Button, Frame, StringVar, filedialog, messagebox
from tkinter.font import Font
from tkinter.ttk import Combobox
from typing import Optional

from patch import DLL_RELATIVE_PATH, find_installed_games, patch_dll, restore_dll


def get_app_path(dll_path: Path) -> Optional[Path]:
    """Get .app bundle path from DLL path."""
    for parent in dll_path.parents:
        if parent.suffix == ".app":
            return parent
    return None


def codesign_app(app_path: Path) -> bool:
    """Ad-hoc codesign the app bundle."""
    try:
        subprocess.run(
            ["codesign", "--force", "--deep", "--sign", "-", str(app_path)],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


class PatcherApp:
    def __init__(self):
        self.root = Tk()
        self.root.title("Steam Input Controller Patch for InControl Games")
        self.root.resizable(False, False)

        self.dll_path: Optional[Path] = None
        self.installed_games: list[tuple[str, Path]] = []
        self.setup_ui()
        self.detect_games()

    def setup_ui(self):
        self.root.configure(padx=20, pady=20)

        title_font = Font(size=14, weight="bold")
        Label(self.root, text="Steam Input Patch", font=title_font).pack()
        Label(self.root, text="for InControl Games").pack()

        Frame(self.root, height=10).pack()

        self.game_frame = Frame(self.root)
        self.game_frame.pack(pady=5)

        self.game_var = StringVar()
        self.game_selector = Combobox(
            self.game_frame, textvariable=self.game_var,
            state="readonly", width=25
        )
        self.game_selector.bind("<<ComboboxSelected>>", self._on_game_selected)

        self.status = Label(self.root, text="No game selected", fg="gray")
        self.status.pack(pady=10)

        self.path_label = Label(self.root, text="", fg="gray", wraplength=300, justify="center")
        self.path_label.pack()

        Frame(self.root, height=10).pack()

        btn_frame = Frame(self.root)
        btn_frame.pack(pady=10)

        self.patch_btn = Button(btn_frame, text="Patch", width=10, command=self.do_patch, state="disabled")
        self.patch_btn.pack(side="left", padx=5)

        self.restore_btn = Button(btn_frame, text="Restore", width=10, command=self.do_restore, state="disabled")
        self.restore_btn.pack(side="left", padx=5)

        self.codesign_btn = Button(btn_frame, text="Codesign", width=10, command=self.do_codesign, state="disabled")
        self.codesign_btn.pack(side="left", padx=5)

        Button(self.root, text="Select Different App...", command=self.browse).pack(pady=5)

    def detect_games(self):
        self.installed_games = find_installed_games()

        if len(self.installed_games) == 0:
            self.browse()
        elif len(self.installed_games) == 1:
            name, dll_path = self.installed_games[0]
            use_it = messagebox.askyesno(
                "Game Found",
                f"Found {name} in Steam library.\n\nUse this version?"
            )
            if use_it:
                self.set_dll(dll_path, name)
            else:
                self.browse()
        else:
            self.game_selector.pack()
            self.game_selector["values"] = [name for name, _ in self.installed_games]
            self.game_selector.current(0)
            self._on_game_selected()

    def _on_game_selected(self, _event=None):
        idx = self.game_selector.current()
        if idx < 0:
            return
        name, dll_path = self.installed_games[idx]
        self.set_dll(dll_path, name)

    def browse(self):
        app_path = filedialog.askopenfilename(
            title="Select game .app",
            filetypes=[("Application", "*.app")],
            initialdir=Path.home()
        )
        if app_path:
            dll_path = Path(app_path) / DLL_RELATIVE_PATH
            if dll_path.exists():
                self.set_dll(dll_path, Path(app_path).stem)
            else:
                messagebox.showerror("Error", "Assembly-CSharp.dll not found in selected app")

    def set_dll(self, path: Path, game_name: str = ""):
        self.dll_path = path
        self.path_label.config(text=str(path.parent))
        self.patch_btn.config(state="normal")
        self.codesign_btn.config(state="normal")

        backup = path.with_suffix(".dll.bak")
        if backup.exists():
            self.status.config(text=f"{game_name} (backup exists)" if game_name else "Ready (backup exists)", fg="green")
            self.restore_btn.config(state="normal")
        else:
            self.status.config(text=game_name or "Ready", fg="green")
            self.restore_btn.config(state="disabled")

    def do_patch(self):
        if not self.dll_path:
            return
        if patch_dll(self.dll_path):
            self.status.config(text="Patched!", fg="green")
            self.restore_btn.config(state="normal")
            messagebox.showinfo(
                "Success",
                "Patch applied!\n\nNow enable Steam Input:\nSteam -> Game -> Properties -> Controller"
            )
        else:
            self.status.config(text="Patch failed", fg="red")
            messagebox.showerror("Error", "Patch failed - strings not found or already patched")

    def do_restore(self):
        if not self.dll_path:
            return
        if restore_dll(self.dll_path):
            self.status.config(text="Restored", fg="green")
            messagebox.showinfo("Success", "Restored from backup!")
        else:
            self.status.config(text="Restore failed", fg="red")
            messagebox.showerror("Error", "No backup found")

    def do_codesign(self):
        if not self.dll_path:
            return
        app_path = get_app_path(self.dll_path)
        if not app_path:
            messagebox.showerror("Error", "Could not find .app bundle")
            return
        if codesign_app(app_path):
            self.status.config(text="Codesigned!", fg="green")
            messagebox.showinfo("Success", f"App signed:\n{app_path.name}")
        else:
            self.status.config(text="Codesign failed", fg="red")
            messagebox.showerror("Error", "Codesign failed")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    PatcherApp().run()
