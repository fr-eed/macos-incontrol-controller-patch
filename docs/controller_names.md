# Controller Names in Tricky Towers (InControl)
# Extracted from Assembly-CSharp.dll
#
# These are the joystick names that InControl recognizes.
# Names ending with "on Mac" are macOS-specific profiles.

## Mac-specific controller names (for patching):
```il
Afterglow Prismatic Xbox One Controller on Mac
Air Flo Wired PS3 Controller on Mac
BETAOP Controller on Mac
Batarang Controller on Mac
Big Ben Controller on Mac
EA Sports Controller on Mac
GameStop Controller on Mac
Guitar Hero Controller on Mac
Hori Controller on Mac
Hori EX2 Controller on Mac
Hori Pad EX Turbo Controller on Mac
Hori Xbox One Controller on Mac
Joytek Xbox 360 Controller on Mac
Logitech Chill Stream Controller on Mac
Logitech Controller on Mac
Logitech F310 Controller on Mac
Logitech F510 Controller on Mac
Logitech F710 Controller on Mac
MLG Controller on Mac
Mad Catz COD Controller on Mac
Mad Catz Controller on Mac
Mad Catz FightPad Controller on Mac
Mad Catz Micro Controller on Mac
Mad Catz MicroCon Controller on Mac
Mad Catz Pro Controller on Mac
Mat Catz Controller on Mac
Microsoft Xbox 360 Controller on Mac
Microsoft Xbox Controller on Mac
Microsoft Xbox One Controller on Mac
Microsoft Xbox One Elite Controller on Mac
Nacon GC-100XF Controller on Mac
PDP Afterglow Controller on Mac
PDP Marvel Controller on Mac
PDP Tron Controller on Mac
PDP Versus Controller on Mac
PDP Xbox One Controller on Mac
POWER A FUS1ON Tournament Controller on Mac
PlayStation 3 Controller on Mac
PlayStation 4 Controller on Mac
PlayStation 4 Controller on Mac via Steam Link
Power A Mini Xbox One Controller on Mac
PowerA Airflow Controller on Mac
PowerA Mini Controller on Mac
PowerA Mini Pro Ex Controller on Mac
PowerA Spectra Illuminated Controller on Mac
Pro EX Xbox 360 Controller on Mac
Pro EX Xbox One Controller on Mac
Razer Onza Controller on Mac
Razer Onza TE Controller on Mac
Razer Sabertooth Elite Controller on Mac
Razer Serval Controller on Mac
Razer Strike Controller on Mac
Razer Wildcat Controller on Mac
Red Octane Controller on Mac
Rock Candy Controller on Mac
Rock Candy Xbox 360 Controller on Mac
Rock Candy Xbox One Controller on Mac
Saitek Xbox 360 Controller on Mac
TSZ Pelican Controller on Mac
Thrustmaster GPX Controller on Mac
Trust Predator Joystick on Mac
XBox 360 Controller on Mac
iBuffalo Classic Controller on Mac

```

## Generic controller names (cross-platform):

```il
Microsoft Wireless 360 Controller
Microsoft Xbox 360 Controller
Microsoft Xbox Controller
Microsoft Xbox One Controller
Microsoft Xbox One Elite Controller
Microsoft Xbox One Wired Controller
Microsoft StreamingGamePad-1
Xbox 360 Controller
Xbox 360 Wired Controller
Xbox 360 Wireless Controller
Xbox Controller
Xbox One Controller
Xbox One Controller on OSX
Xbox One Elite Controller
XBox 360 Controller
XBox One Controller
Wireless Controller
Unknown Controller
Unknown Gamepad
Generic Controller
Generic Gamepad
```

## Regex pattern found:

```il
360|xbox|catz
```

## Notes:

- Steam Input presents controllers as "Microsoft GamePad-1", "Microsoft GamePad-2", etc.
- These names don't match any existing profile.

## Alternative Fix:

Another approach is to enable `NativeInputEnableMFi = true` in InControl's `InControlManager.OnEnable()` method. This makes InControl use Apple's MFi (Made for iPhone) native controller framework instead of matching joystick names.