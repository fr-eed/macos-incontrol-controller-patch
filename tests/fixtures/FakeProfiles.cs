// Fake Assembly-CSharp.dll for tests

namespace InControl
{
    public class Xbox360MacProfile
    {
        public string[] JoystickNames = new string[]
        {
            "Microsoft Wireless 360 Controller",
            "Mad Catz, Inc. Mad Catz FPS Pro GamePad",
            "Mad Catz, Inc. MadCatz Call of Duty GamePad",
            "©Microsoft Corporation Controller",
        };
    }

    public class NativeMacProfiles
    {
        public string[] JoystickNames = new string[]
        {
            "BDA PS3 Airflo wired controller",
            " USB,2-axis 8-button gamepad",
            "Zeroplus PS Vibration Feedback Converter",
            "Zeroplus PS Vibration Feedback Converter ",
            "Logitech Logitech Dual Action",
            "Logitech Gamepad F310",
            "Logitech Logitech RumblePad 2 USB",
            "Logitech Rumble Gamepad F510",
            "Logitech Logitech Cordless RumblePad 2",
            "Unknown Moga Pro HID",
            "Unknown Gamepad",
            "Sony PLAYSTATION(R)3 Controller",
            "SHENGHIC 2009/0708ZXW-V1Inc. PLAYSTATION(R)3Conteroller",
            "SZMY-POWER CO.,LTD. GAMEPAD 3 TURBO",
            "Gasia Co.,Ltd PS(R) Gamepad",
            "Unknown Wireless Controller",
            "Sony Computer Entertainment Wireless Controller",
            "Sony Interactive Entertainment Wireless Controller",
            "Razer Razer Serval",
            "Unknown Razer Serval",
            "DragonRise Inc.   Generic   USB  Joystick  ",
            "Unknown Zeemote: SteelSeries FREE",
            "Microsoft Xbox One Wired Controller",
            "©Microsoft Corporation Xbox Original Wired Controller",
            "Sony Interactive Entertainment DUALSHOCK®4 USB Wireless Adaptor",
        };
    }

    public class Decoys
    {
        public string[] Names = new string[]
        {
            "Unknown Gamepad Pro",
            "Microsoft Wireless 360 Controller for Windows",
            "Press Start",
        };
    }

    public static class GameInfo
    {
#if V2
        public const string Version = "GAME-V2";
#else
        public const string Version = "GAME-V1";
#endif
    }
}
