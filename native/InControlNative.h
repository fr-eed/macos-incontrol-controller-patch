// From https://github.com/TheNils96/ds4-bluetooth-fix-mac (MIT License)
// C API of the replacement InControlNative plugin.
// Struct layouts and signatures match the P/Invoke declarations of InControl 1.6.17
// (InControl.Native, NativeDeviceInfo, NativeInputOptions, NativeVersionInfo).
#ifndef INCONTROL_NATIVE_H
#define INCONTROL_NATIVE_H

#include <stdint.h>

#define DS4_NUM_BUTTONS 18
#define DS4_NUM_ANALOGS 6

typedef struct {
    uint16_t updateRate;
    int32_t enableXInput;
    int32_t preventSleep;
} NativeInputOptions;

typedef struct {
    uint32_t major, minor, patch, build;
} NativeVersionInfo;

typedef struct {
    char name[128];
    char location[128];
    char serialNumber[64];
    uint16_t vendorID;
    uint16_t productID;
    uint32_t versionNumber;
    uint16_t driverType;    // NativeDeviceDriverType: 1 = HID
    uint16_t transportType; // NativeDeviceTransportType: 1 = USB, 2 = Bluetooth
    uint32_t numButtons;
    uint32_t numAnalogs;
} NativeDeviceInfo;

void InControl_Init(NativeInputOptions options);
void InControl_Stop(void);
void InControl_GetVersionInfo(NativeVersionInfo *info);
int32_t InControl_GetDeviceInfo(uint32_t handle, NativeDeviceInfo *info);
int32_t InControl_GetDeviceState(uint32_t handle, int16_t **state);
int32_t InControl_GetDeviceEvents(uint32_t **events);
void InControl_SetHapticState(uint32_t handle, uint8_t motor0, uint8_t motor1);
void InControl_SetLightColor(uint32_t handle, uint8_t red, uint8_t green, uint8_t blue);
void InControl_SetLightFlash(uint32_t handle, uint8_t on, uint8_t off);

#endif
