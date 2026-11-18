// From https://github.com/TheNils96/ds4-bluetooth-fix-mac (MIT License)
// Drop-in replacement for InControl's InControlNative.bundle (macOS) that reads
// DualShock 4 controllers from their raw HID reports. Unlike the original plugin
// it understands the extended Bluetooth report (0x11) macOS switches DS4s into,
// and it gives every controller its own handle (no Steam virtual pads).
//
// The C API mirrors the P/Invoke declarations in InControl 1.6.17 (Human Fall Flat).
// Device state layout matches InControl's PlayStation4MacProfile (native):
//   buttons[18]: 0 Square, 1 Cross, 2 Circle, 3 Triangle, 4 L1, 5 R1, 6 L2, 7 R2,
//                8 Share, 9 Options, 10 L3, 11 R3, 12 PS, 13 Touchpad,
//                14 DPad Up, 15 DPad Down, 16 DPad Left, 17 DPad Right
//   analogs[6]:  0 LX, 1 LY, 2 RX, 3 RY (right/down positive), 4 L2, 5 R2
//   values are int16; buttons: pressed = 32767, released = -32767;
//   triggers: released = -32767, full = 32767.

#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/hid/IOHIDManager.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "InControlNative.h"

#define EXPORT __attribute__((visibility("default")))

#define NUM_BUTTONS DS4_NUM_BUTTONS
#define NUM_ANALOGS DS4_NUM_ANALOGS
#define MAX_DEVICES 8
#define REPORT_BUF 128
#define SONY_VID 0x054c

typedef struct {
    int used;
    uint32_t handle;
    IOHIDDeviceRef device;
    NativeDeviceInfo info;
    uint8_t report[REPORT_BUF];
    int16_t state[NUM_BUTTONS + NUM_ANALOGS];     // written on HID thread
    int16_t readState[NUM_BUTTONS + NUM_ANALOGS]; // handed to the game
} Device;

static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static Device devices[MAX_DEVICES];
static uint32_t nextHandle = 1;
static uint32_t attachedQueue[MAX_DEVICES * 4], detachedQueue[MAX_DEVICES * 4];
static int numAttached, numDetached;
static uint32_t eventBuffer[2 + MAX_DEVICES * 8];

static pthread_t hidThread;
static CFRunLoopRef hidRunLoop;
static IOHIDManagerRef manager;
static int running;
static pthread_mutex_t startLock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t startCond = PTHREAD_COND_INITIALIZER;
static int started;

static int is_ds4(uint16_t vid, uint16_t pid) {
    // DS4 v1, DS4 v2 (incl. most clones), Sony wireless adapter
    return vid == SONY_VID && (pid == 0x05c4 || pid == 0x09cc || pid == 0x0ba0);
}

static long prop_long(IOHIDDeviceRef d, CFStringRef key) {
    long v = 0;
    CFTypeRef r = IOHIDDeviceGetProperty(d, key);
    if (r && CFGetTypeID(r) == CFNumberGetTypeID()) CFNumberGetValue(r, kCFNumberLongType, &v);
    return v;
}

static void prop_str(IOHIDDeviceRef d, CFStringRef key, char *buf, size_t n) {
    buf[0] = 0;
    CFTypeRef r = IOHIDDeviceGetProperty(d, key);
    if (r && CFGetTypeID(r) == CFStringGetTypeID()) CFStringGetCString(r, buf, n, kCFStringEncodingUTF8);
}

static int16_t axis(uint8_t v) {
    // 0..255 -> -32767..32767
    return (int16_t)((int32_t)v * 65534 / 255 - 32767);
}

static int16_t button(int pressed) {
    return pressed ? 32767 : -32767;
}

static void reset_state(int16_t *s) {
    for (int i = 0; i < NUM_BUTTONS; i++) s[i] = button(0);
    for (int i = 0; i < 4; i++) s[NUM_BUTTONS + i] = 0;
    s[NUM_BUTTONS + 4] = s[NUM_BUTTONS + 5] = -32767;
}

// Decode a DS4 input report. `r` starts with the report ID.
// USB / basic Bluetooth report 0x01: data at r[1]; extended Bluetooth 0x11: data at r[3].
static void decode(Device *dev, const uint8_t *r, CFIndex len) {
    int base;
    if (r[0] == 0x01 && len >= 10) base = 1;
    else if (r[0] == 0x11 && len >= 12) base = 3;
    else return;

    const uint8_t *p = r + base;
    uint8_t b0 = p[4], b1 = p[5], b2 = p[6], hat = b0 & 0x0f;
    int16_t *s = dev->state;

    s[0] = button(b0 & 0x10);
    s[1] = button(b0 & 0x20);
    s[2] = button(b0 & 0x40);
    s[3] = button(b0 & 0x80);
    for (int i = 0; i < 8; i++) s[4 + i] = button(b1 & (1 << i));
    s[12] = button(b2 & 0x01);
    s[13] = button(b2 & 0x02);
    s[14] = button(hat == 7 || hat == 0 || hat == 1);
    s[15] = button(hat == 3 || hat == 4 || hat == 5);
    s[16] = button(hat == 5 || hat == 6 || hat == 7);
    s[17] = button(hat == 1 || hat == 2 || hat == 3);

    s[NUM_BUTTONS + 0] = axis(p[0]);
    s[NUM_BUTTONS + 1] = axis(p[1]);
    s[NUM_BUTTONS + 2] = axis(p[2]);
    s[NUM_BUTTONS + 3] = axis(p[3]);
    s[NUM_BUTTONS + 4] = axis(p[7]);
    s[NUM_BUTTONS + 5] = axis(p[8]);
}

static void on_report(void *ctx, IOReturn res, void *sender, IOHIDReportType type,
                      uint32_t reportID, uint8_t *report, CFIndex len) {
    Device *dev = ctx;
    if (len < 1) return;
    uint8_t tmp[REPORT_BUF + 1];
    const uint8_t *r = report;
    // Make sure the buffer starts with the report ID.
    if (report[0] != reportID && len < REPORT_BUF) {
        tmp[0] = (uint8_t)reportID;
        memcpy(tmp + 1, report, len);
        r = tmp;
        len++;
    }
    pthread_mutex_lock(&lock);
    if (dev->used) decode(dev, r, len);
    pthread_mutex_unlock(&lock);
}

static void on_match(void *ctx, IOReturn res, void *sender, IOHIDDeviceRef d) {
    uint16_t vid = prop_long(d, CFSTR(kIOHIDVendorIDKey));
    uint16_t pid = prop_long(d, CFSTR(kIOHIDProductIDKey));
    if (!is_ds4(vid, pid)) return;

    pthread_mutex_lock(&lock);
    Device *dev = NULL;
    for (int i = 0; i < MAX_DEVICES; i++) {
        if (devices[i].used && devices[i].device == d) { pthread_mutex_unlock(&lock); return; }
        if (!dev && !devices[i].used) dev = &devices[i];
    }
    if (!dev) { pthread_mutex_unlock(&lock); return; }

    memset(dev, 0, sizeof *dev);
    dev->used = 1;
    dev->device = d;
    dev->handle = nextHandle++;
    NativeDeviceInfo *info = &dev->info;
    prop_str(d, CFSTR(kIOHIDProductKey), info->name, sizeof info->name);
    if (!info->name[0]) strcpy(info->name, "Wireless Controller");
    snprintf(info->location, sizeof info->location, "0x%lx", prop_long(d, CFSTR(kIOHIDLocationIDKey)));
    prop_str(d, CFSTR(kIOHIDSerialNumberKey), info->serialNumber, sizeof info->serialNumber);
    info->vendorID = vid;
    info->productID = pid;
    info->versionNumber = (uint32_t)prop_long(d, CFSTR(kIOHIDVersionNumberKey));
    info->driverType = 1;
    char transport[64];
    prop_str(d, CFSTR(kIOHIDTransportKey), transport, sizeof transport);
    info->transportType = strcmp(transport, "Bluetooth") == 0 ? 2 : strcmp(transport, "USB") == 0 ? 1 : 0;
    info->numButtons = NUM_BUTTONS;
    info->numAnalogs = NUM_ANALOGS;
    reset_state(dev->state);
    reset_state(dev->readState);
    if (numAttached < (int)(sizeof attachedQueue / sizeof *attachedQueue))
        attachedQueue[numAttached++] = dev->handle;
    pthread_mutex_unlock(&lock);

    CFRetain(d);
    IOHIDDeviceRegisterInputReportCallback(d, dev->report, sizeof dev->report, on_report, dev);
}

static void on_remove(void *ctx, IOReturn res, void *sender, IOHIDDeviceRef d) {
    pthread_mutex_lock(&lock);
    for (int i = 0; i < MAX_DEVICES; i++) {
        Device *dev = &devices[i];
        if (dev->used && dev->device == d) {
            dev->used = 0;
            if (numDetached < (int)(sizeof detachedQueue / sizeof *detachedQueue))
                detachedQueue[numDetached++] = dev->handle;
            pthread_mutex_unlock(&lock);
            IOHIDDeviceRegisterInputReportCallback(d, dev->report, sizeof dev->report, NULL, NULL);
            CFRelease(d);
            return;
        }
    }
    pthread_mutex_unlock(&lock);
}

static CFDictionaryRef match_usage(int page, int usage) {
    CFMutableDictionaryRef m = CFDictionaryCreateMutable(NULL, 0, &kCFTypeDictionaryKeyCallBacks,
                                                         &kCFTypeDictionaryValueCallBacks);
    CFNumberRef p = CFNumberCreate(NULL, kCFNumberIntType, &page);
    CFNumberRef u = CFNumberCreate(NULL, kCFNumberIntType, &usage);
    CFDictionarySetValue(m, CFSTR(kIOHIDDeviceUsagePageKey), p);
    CFDictionarySetValue(m, CFSTR(kIOHIDDeviceUsageKey), u);
    CFRelease(p);
    CFRelease(u);
    return m;
}

static void *hid_main(void *arg) {
    manager = IOHIDManagerCreate(kCFAllocatorDefault, kIOHIDOptionsTypeNone);
    CFDictionaryRef m[2] = { match_usage(kHIDPage_GenericDesktop, kHIDUsage_GD_GamePad),
                             match_usage(kHIDPage_GenericDesktop, kHIDUsage_GD_Joystick) };
    CFArrayRef arr = CFArrayCreate(NULL, (const void **)m, 2, &kCFTypeArrayCallBacks);
    IOHIDManagerSetDeviceMatchingMultiple(manager, arr);
    CFRelease(arr);
    CFRelease(m[0]);
    CFRelease(m[1]);
    IOHIDManagerRegisterDeviceMatchingCallback(manager, on_match, NULL);
    IOHIDManagerRegisterDeviceRemovalCallback(manager, on_remove, NULL);
    hidRunLoop = CFRunLoopGetCurrent();
    IOHIDManagerScheduleWithRunLoop(manager, hidRunLoop, kCFRunLoopDefaultMode);
    IOHIDManagerOpen(manager, kIOHIDOptionsTypeNone);

    pthread_mutex_lock(&startLock);
    started = 1;
    pthread_cond_signal(&startCond);
    pthread_mutex_unlock(&startLock);

    while (running)
        CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.25, false);

    IOHIDManagerUnscheduleFromRunLoop(manager, hidRunLoop, kCFRunLoopDefaultMode);
    IOHIDManagerClose(manager, kIOHIDOptionsTypeNone);
    CFRelease(manager);
    manager = NULL;
    return NULL;
}

EXPORT void InControl_Init(NativeInputOptions options) {
    if (running) return;
    pthread_mutex_lock(&lock);
    memset(devices, 0, sizeof devices);
    numAttached = numDetached = 0;
    pthread_mutex_unlock(&lock);
    running = 1;
    started = 0;
    pthread_create(&hidThread, NULL, hid_main, NULL);
    pthread_mutex_lock(&startLock);
    while (!started) pthread_cond_wait(&startCond, &startLock);
    pthread_mutex_unlock(&startLock);
}

EXPORT void InControl_Stop(void) {
    if (!running) return;
    running = 0;
    if (hidRunLoop) CFRunLoopStop(hidRunLoop);
    pthread_join(hidThread, NULL);
    hidRunLoop = NULL;
    pthread_mutex_lock(&lock);
    for (int i = 0; i < MAX_DEVICES; i++) {
        if (devices[i].used) {
            CFRelease(devices[i].device);
            devices[i].used = 0;
        }
    }
    numAttached = numDetached = 0;
    pthread_mutex_unlock(&lock);
}

EXPORT void InControl_GetVersionInfo(NativeVersionInfo *info) {
    info->major = 1;
    info->minor = 6;
    info->patch = 17;
    info->build = 9143;
}

EXPORT int32_t InControl_GetDeviceInfo(uint32_t handle, NativeDeviceInfo *info) {
    pthread_mutex_lock(&lock);
    for (int i = 0; i < MAX_DEVICES; i++) {
        if (devices[i].used && devices[i].handle == handle) {
            *info = devices[i].info;
            pthread_mutex_unlock(&lock);
            return 1;
        }
    }
    pthread_mutex_unlock(&lock);
    return 0;
}

EXPORT int32_t InControl_GetDeviceState(uint32_t handle, int16_t **state) {
    pthread_mutex_lock(&lock);
    for (int i = 0; i < MAX_DEVICES; i++) {
        Device *dev = &devices[i];
        if (dev->used && dev->handle == handle) {
            memcpy(dev->readState, dev->state, sizeof dev->state);
            *state = dev->readState;
            pthread_mutex_unlock(&lock);
            return 1;
        }
    }
    pthread_mutex_unlock(&lock);
    return 0;
}

// Event buffer layout: [numAttached, handles..., numDetached, handles...]
EXPORT int32_t InControl_GetDeviceEvents(uint32_t **events) {
    pthread_mutex_lock(&lock);
    if (numAttached == 0 && numDetached == 0) {
        pthread_mutex_unlock(&lock);
        return 0;
    }
    int n = 0;
    eventBuffer[n++] = numAttached;
    for (int i = 0; i < numAttached; i++) eventBuffer[n++] = attachedQueue[i];
    eventBuffer[n++] = numDetached;
    for (int i = 0; i < numDetached; i++) eventBuffer[n++] = detachedQueue[i];
    numAttached = numDetached = 0;
    pthread_mutex_unlock(&lock);
    *events = eventBuffer;
    return n;
}

// Rumble and light bar are not used by Human Fall Flat on Mac; accept and ignore.
EXPORT void InControl_SetHapticState(uint32_t handle, uint8_t motor0, uint8_t motor1) {}
EXPORT void InControl_SetLightColor(uint32_t handle, uint8_t red, uint8_t green, uint8_t blue) {}
EXPORT void InControl_SetLightFlash(uint32_t handle, uint8_t on, uint8_t off) {}
