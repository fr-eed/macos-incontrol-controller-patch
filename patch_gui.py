#!/usr/bin/env python3
"""
Steam Input Controller Patch for InControl Games - GUI
"""

import subprocess
import tempfile
import plistlib
import sys
from pathlib import Path
from typing import Optional

# Catch error if tkinter is not available
try:
    from tkinter import Tk, Frame, PhotoImage, filedialog, messagebox
    from tkinter import ttk
except ImportError:
    print("❌ Error: The 'tkinter' GUI module was not found in your Python installation.")
    print("\nOn macOS (especially when using Homebrew), the Tkinter module is often separated")
    print("from the main Python installation to minimize system dependencies.")
    print("\n[Solution 1] Install the Tkinter module for your specific Python version:")
    print("           brew install python-tk@<your_python_version> (e.g., brew install python-tk@3.14)")
    print("\n[Solution 2] Skip the GUI and run the CLI script directly:")
    print("           python3 patch.py\n")
    sys.exit(1)

from patch import DLL_RELATIVE_PATH, find_installed_games, patch_dll, restore_dll


def get_app_icon(app_path: Path, size: int = 32) -> Optional[PhotoImage]:
    """Extract app icon from .app bundle and return as PhotoImage."""
    try:
        # Find icon file from Info.plist
        info_plist = app_path / "Contents" / "Info.plist"
        if info_plist.exists():
            with open(info_plist, "rb") as f:
                plist = plistlib.load(f)
            icon_name = plist.get("CFBundleIconFile", "")
            if not icon_name.endswith(".icns"):
                icon_name += ".icns"
            icns_path = app_path / "Contents" / "Resources" / icon_name
        else:
            # Fallback: find any .icns file
            icns_files = list((app_path / "Contents" / "Resources").glob("*.icns"))
            icns_path = icns_files[0] if icns_files else None

        if not icns_path or not icns_path.exists():
            return None

        # Convert .icns to PNG using sips (macOS built-in)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        subprocess.run(
            ["sips", "-s", "format", "png", "-z", str(size), str(size),
             str(icns_path), "--out", tmp_path],
            capture_output=True, check=True
        )

        return PhotoImage(file=tmp_path)
    except Exception as e:
        print(f"Could not load app icon: {e}", file=sys.stderr)
        return None


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
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Steam Input Patch")
        self.root.resizable(False, False)

        self.dll_path: Optional[Path] = None
        self.installed_games: list[tuple[str, Path]] = []
        self.icons: list[PhotoImage] = []  # Keep references to prevent garbage collection

        self.setup_ui()
        self.detect_games()

    def setup_ui(self) -> None:
        self.root.configure(padx=20, pady=20)

        # Configure treeview style for taller rows
        style = ttk.Style()
        style.configure("Treeview", rowheight=40, font=("Helvetica Neue", 12))

        # Title
        ttk.Label(self.root, text="Steam Input Patch", font=("Helvetica Neue", 16, "bold")).pack()
        ttk.Label(self.root, text="for InControl Games", foreground="gray").pack()

        ttk.Frame(self.root, height=10).pack()

        ttk.Label(self.root, text="Select a game:", foreground="gray").pack(anchor="w")

        self.game_frame = ttk.Frame(self.root)
        self.game_frame.pack(pady=5, fill="x")

        # Treeview with icon and name columns
        self.game_tree = ttk.Treeview(
            self.game_frame, columns=("name",), show="tree",
            height=5, selectmode="browse"
        )
        self.game_tree.column("#0", width=50, stretch=False)  # Icon column
        self.game_tree.column("name", width=260)
        self.game_tree.pack(fill="x")
        self.game_tree.bind("<<TreeviewSelect>>", self._on_game_selected)

        self.status = ttk.Label(self.root, text="No game selected", foreground="gray")
        self.status.pack(pady=10)

        self.path_label = ttk.Label(self.root, text="", foreground="gray", wraplength=300, justify="center")
        self.path_label.pack()

        ttk.Frame(self.root, height=10).pack()

        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)

        self.patch_btn = ttk.Button(btn_frame, text="Patch", width=10, command=self.do_patch, state="disabled")
        self.patch_btn.pack(side="left", padx=5)

        self.restore_btn = ttk.Button(btn_frame, text="Restore", width=10, command=self.do_restore, state="disabled")
        self.restore_btn.pack(side="left", padx=5)

        self.codesign_btn = ttk.Button(btn_frame, text="Codesign", width=10, command=self.do_codesign, state="disabled")
        self.codesign_btn.pack(side="left", padx=5)

    def detect_games(self) -> None:
        self.installed_games = find_installed_games()

        # Populate tree with found games
        for i, (name, dll_path) in enumerate(self.installed_games):
            app_path = get_app_path(dll_path)
            icon = get_app_icon(app_path) if app_path else None
            if icon:
                self.icons.append(icon)
                self.game_tree.insert("", "end", iid=str(i), image=icon, values=(name,))
            else:
                self.game_tree.insert("", "end", iid=str(i), text="", values=(name,))

        # Add option to browse for custom game
        self.game_tree.insert("", "end", iid="browse", text=" 🔍", values=("Select other app...",))

        if not self.installed_games:
            self.status.config(text="No games found", foreground="gray")
        else:
            self.status.config(text=f"Found {len(self.installed_games)} game(s)", foreground="gray")

    def _on_game_selected(self, _event=None) -> None:
        selection = self.game_tree.selection()
        if not selection:
            return
        item_id = selection[0]

        # "browse" item is for selecting other app
        if item_id == "browse":
            self.game_tree.selection_remove("browse")
            self.browse()
            return

        idx = int(item_id)
        name, dll_path = self.installed_games[idx]
        self.set_dll(dll_path, name)

    def browse(self) -> None:
        app_path_str = self._choose_app()
        if app_path_str:
            app_path = Path(app_path_str)
            dll_path = app_path / DLL_RELATIVE_PATH
            if dll_path.exists():
                name = app_path.stem
                idx = len(self.installed_games)
                self.installed_games.append((name, dll_path))

                # Add to tree before "browse" item
                icon = get_app_icon(app_path)
                if icon:
                    self.icons.append(icon)
                    self.game_tree.insert("", idx, iid=str(idx), image=icon, values=(name,))
                else:
                    self.game_tree.insert("", idx, iid=str(idx), text="", values=(name,))

                # Select it
                self.game_tree.selection_set(str(idx))
                self.set_dll(dll_path, name)
            else:
                messagebox.showerror("Error", "Assembly-CSharp.dll not found in selected app")

    def _choose_app(self) -> str:
        """Pick a .app bundle natively on macOS, or fallback to file dialog."""
        result = subprocess.run(
            ["osascript", "-e",
             'POSIX path of (choose file of type {"com.apple.application-bundle"} '
             'with prompt "Select game .app")'],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip().rstrip("/")
        if "-128" in result.stderr:  # user cancelled
            return ""
        return filedialog.askopenfilename(
            title="Select game .app",
            filetypes=[("Application", "*.app")],
            initialdir=Path.home()
        )

    def set_dll(self, path: Path, game_name: str = "") -> None:
        self.dll_path = path
        self.path_label.config(text=str(path.parent))
        self.patch_btn.config(state="normal")
        self.codesign_btn.config(state="normal")

        backup = path.with_suffix(".dll.bak")
        if backup.exists():
            self.status.config(text=f"{game_name} (backup exists)" if game_name else "Ready (backup exists)", foreground="green")
            self.restore_btn.config(state="normal")
        else:
            self.status.config(text=game_name or "Ready", foreground="green")
            self.restore_btn.config(state="disabled")

    def do_patch(self) -> None:
        if not self.dll_path:
            return
        if patch_dll(self.dll_path):
            self.status.config(text="Patched!", foreground="green")
            self.restore_btn.config(state="normal")
            messagebox.showinfo(
                "Success",
                "Patch applied!\n\nNow enable Steam Input:\nSteam -> Game -> Properties -> Controller"
            )
        else:
            self.status.config(text="Patch failed", foreground="red")
            messagebox.showerror("Error", "Patch failed - strings not found or already patched")

    def do_restore(self) -> None:
        if not self.dll_path:
            return
        if restore_dll(self.dll_path):
            self.status.config(text="Restored", foreground="green")
            messagebox.showinfo("Success", "Restored from backup!")
        else:
            self.status.config(text="Restore failed", foreground="red")
            messagebox.showerror("Error", "No backup found")

    def do_codesign(self) -> None:
        if not self.dll_path:
            return
        app_path = get_app_path(self.dll_path)
        if not app_path:
            messagebox.showerror("Error", "Could not find .app bundle")
            return
        if codesign_app(app_path):
            self.status.config(text="Codesigned!", foreground="green")
            messagebox.showinfo("Success", f"App signed:\n{app_path.name}")
        else:
            self.status.config(text="Codesign failed", foreground="red")
            messagebox.showerror("Error", "Codesign failed")

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = PatcherApp()
    app.run()


if __name__ == "__main__":
    main()
