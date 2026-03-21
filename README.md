# Steam Input Controller Patch for InControl Games (macOS)

Fixes controller support on macOS by patching games to recognize Steam Input's virtual controllers.

## Supported Games

- Tricky Towers
- Overcooked! 2

## Problem

These games use InControl for input handling. On macOS, Steam Input presents controllers as "Microsoft GamePad-1", "Microsoft GamePad-2", etc. These names don't match any built-in InControl profile, causing controllers to appear as "Unknown Device".

## Solution

Patches `Assembly-CSharp.dll` to replace Xbox360MacProfile's JoystickNames with Steam Input controller names:

| Original | Replacement |
|----------|-------------|
| Microsoft Wireless 360 Controller | Microsoft GamePad-1 |
| Mad Catz, Inc. Mad Catz FPS Pro GamePad | Microsoft GamePad-2 |
| Mad Catz, Inc. MadCatz Call of Duty GamePad | Microsoft GamePad-3 |
| ©Microsoft Corporation Controller | Microsoft GamePad-4 |

## Usage

### GUI (recommended)

```bash
python3 patch_gui.py
```

Automatically detects supported games in the default Steam library folder; games installed in other Steam library locations must be selected or provided manually.

### Command Line

```bash
python3 patch.py                        # Patch all installed games
python3 patch.py /path/to/dll           # Patch specific DLL
python3 patch.py --restore              # Restore all installed games
python3 patch.py --restore /path/to/dll # Restore specific DLL
```

### After Patching

Enable Steam Input:
1. Steam -> Right-click the game -> Properties -> Controller
2. Select "Enable Steam Input"

## Tested With

- Tricky Towers (unity.WeirdBeard.Tricky Towers)
- Unity Player 5.5.1p3 (828893732fe0)
- Overcooked! 2

## Notes

- Supports up to 4 controllers
- Backup created automatically (`Assembly-CSharp.dll.bak`)
- Game updates will overwrite the patch
- See `docs/` for technical details
