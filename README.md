# IndexEyeTrackVR
Hardware/Software repo for DIY eye tracking on the Valve Index (and potentially other) VR headset. This is intended to emulate the functionality of existing VR eye tracking solutions, and is particularly focused on feeding eye data into social apps such as VRChat.

This repo represents much of my personal work done alongside/with the [EyeTrackVR Project](https://github.com/RedHawk989/EyeTrackVR).

## **DISCLAIMER**
This is a *work-in-progress* repo and project and should not be expected to contain full, up-to-date documentation, source code, models, or anything else. Don't expect anything here to "just work", or to work at all, nor support to be available for it! 

## **SAFETY** 
This project involves shining near-infrared band light directly at your eyes. If running as designed, we should be operating in safe limits. The eye's natural pupillary light reflex does not trigger for IR light in the same way it does for optical light. This means that if blasted with high intensity IR, the pupil will not constrict to limit the intensity. This is especially important when the pupil can be significantly dialated from the low light intensity in VR.

If something were to happen like a resistor shorting, it would be possible to send significant quantities of IR light into the eye, possibly without the user ever feeling a thing, or noticing beyond the dim red glow becoming a bit brighter. 

Building and using this kind of hardware is done at your own discretion and risk, and any contributors to this project cannot be considered responsible for any adverse effects. 

## **You are responsible for your own safety!**

### Light Intensity calculation

The International Commission on Non-Ionizing Radiation Protection (ICNIRP)'s ["Guidelines of limits of exposure to broad-band incoherent optical radiation (0.38 to 3 µm)"](https://www.icnirp.org/cms/upload/publications/ICNIRPbroadband.pdf) states:

> To avoid thermal injury of the cornea and possible delayed effects on the lens of the eye (cataractogenesis), infrared radiation (780nm < > λ < > 3μm) should be limited to 100 W m⁻² (10 mW cm⁻²) for lengthy exposures (> 1000 s) [...]

Driving an IN-P32ZTIR (850nm, 4.5 mW/sr @ 20 mA) at 5 volts with a 100 ohm resistor gives:

```I = V/R = (5.0 - 1.5)/100 = 0.035 A = 35 mA --> 4.5 mW/sr * (35mA/ 20mA) = 7.875 mW/sr```

The LED distance is approximately 32mm from eye depending on facial geometry, which we round to 3 cm, giving an area of one steradian (sr) at 3cm dist -> 3 cm²/sr. Our final intensity is:

`(7.875 mW/sr) / (3 cm²/sr) = 2.625 mW/cm²`. 

This is within a safe range when operating as designed.



# Software
The ESP32Cam is running [slightly modified Futurabeast face cam firmware](https://github.com/rrazgriz/futura-face-cam) for the moment. In theory, it can run any firmware that outputs an opencv-compatible stream available over the network. [OpenIris](https://github.com/lorow/OpenIris) is being developed specifically for use in the EyeTrackVR Project.

The software side uses a basic Python OpenCV pipeline to process the image data. It requires python3 with `python-osc` and `opencv` available. Other techniques are being implemented elsewhere in the EyeTrackVR Project, including the [VrEyeToolbox](https://github.com/SummerSigh/VrEyeToolbox), which focuses on machine learning approaches to eye parameter estimation.

To run the eyetracking software, configure it as below, and run it in a python environment that has all dependencies satisfied, as noted above. 

The `eyetracking_py` software can read from a stream or video. It's configured with the file `eyetracking_config.cfg` file. Currently, it uses 5 frames to calibrate, which must be present in the `data_path` subpath of `opencv_eyetracking` (`/test_data/` by default). By default, it also looks for a file called `test.mp4` in the configured data path. 

With the data files added, the ROI bounds (start, width) can be defined in x and y. As well, the threshold must be defined to properly isolate the pupil. The software expects a threshold such that pretty much the only thing below/above it is the pupil. These parameters currently take some trial and error to determine. 

Currently, basic gaze (-1 to 1 in x/y axes) and blink (blinking/not blinking) are under development, alongside other methods and features through EyeTrackVR. Calibration procedures are being worked on, but the current direction uses multiple calibration points to define maximum and minimum points as well as blinking/not blinking. OSC is used to transmit data to VRChat.


### Software Todo list
- [x] Improve Framerate (done via Futura firmware?)
- [x] Clean up/refactor code for initial publication
- [ ] Implement Calibration on-the-fly instead of through images
  - 2s intervals - center, left, right, up, down, open, leftclosed, rightclosed
- [ ] Improve Smoothing/Stability (1euro filter/adaptive lerp)
- [ ] Improve Blink Detection
- [ ] Compare/integrate ML approaches


# Hardware
### Hardware Todo List
- [x] Post camera mounts for others (STL)
- [ ] Design ESP32 Mounts
- [ ] Document/Schematic Electronics

## Electronics
Currently, the following hardware is being used for testing. There is no guarantee these will be the final parts, and everything is heavily in flux. Links to AliExpress and Digikey listings for some items are included - these are for reference, and do not represent endorsements. 

- [ESP32CAM Development board with ESP32-CAM-MB programmer](https://www.aliexpress.com/item/1005001900359624.html)
- [OV2640 Camera Module, 75mm Cable, 160 degree lens, 850nm "Night Vision" - no IR cut filter](https://www.aliexpress.com/item/1005003040149873.html)
- [IN-P32ZTIR IR Diode](https://www.digikey.com/en/products/detail/inolux/IN-P32ZTIR/10384796), run at 35 mA - 5V w/ 100ohm resistor 

## 3d Printed Mounts
`cam_ov2640_wideangle_facegasket_mount*.stl` is used to mount the 160-degree, wide-angle variant of the OV2640. The lens snaps into place, and the LED and associated resistor are superglued in place. The assembly is adhered to the lens gasket with double sided tape (3M VHB recommended). The ESP32-Cam (desoldered from its headers after OTA firmware is flashed) is also adhered with tape. 

The mounts were printed in PLA with a 0.4mm nozzle at 0.2mm layer height with no supports. A brim is recommended. These parts are very small, so make sure to print carefully. Any standard 3d printing polymer should work (PLA, PETG, ABS, ASA).

# Licensing
Unless otherwise specified, items in this repository are licensed as such.

|   |   |
|---|---|
| 3D Printing Source Files (STL/3MF) | [CC-BY-SA-4.0](https://spdx.org/licenses/CC-BY-SA-4.0.html) |
| Images/Media | [CC-BY-SA-4.0](https://spdx.org/licenses/CC-BY-SA-4.0.html) |
| Software Files | [MIT](https://spdx.org/licenses/MIT.html) |


Exceptions can be found within individual folders.

# Attributions
Futurabeast - [Futurabeast face cam firmware](https://github.com/rrazgriz/futura-face-cam)

Valve Software - [Index Hardware CAD](https://github.com/ValveSoftware/IndexHardware) (licensed under CC-BY-NC-SA-4.0)

# Media
![Camera/ESP Mounting](./media/camera_esp_mounting_2022-03-22.png)

https://user-images.githubusercontent.com/47901762/160254647-f92e436d-78cc-42f1-9b42-50ed9ba449d1.mp4

https://user-images.githubusercontent.com/47901762/160254653-4695fb8c-6ce4-4c03-9f54-f484273bd840.mp4


