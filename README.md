# 3D Scanner on Android

Structured-light 3D reconstruction using a Samsung Galaxy Beam and a prism to align its projector with the camera's field of view.

Students: Arkadi Godlin, Alex Kligman, Alon Zivrin.

Supervision: Aaron Wetzler.

## Status

**Partial original source recovered. Build and run untested.** `source/` contains 27 unchanged text files from the September 2014 source handoff: 11 Java files, XML resources and original Eclipse/Android project configuration. It is not a complete runnable release.

## Running

The original project uses Eclipse/ADT, Android/Java, OpenCV for Android and a Samsung Galaxy Beam with an aligned prism. `project.properties` targets Android API 11 and references an external OpenCV Library 2.4.4 project. The manifest sets minimum API 8. However, MainActivity requests OpenCV Manager version 2.4.3 at startup. This original version mismatch is preserved and unresolved; no SDK/editor/compiler version beyond these file values was established.

The launcher is `com.project.activities.MainActivity`; reconstruction is in `logic/Reconstructor.java`, and mesh display uses `activities/MeshViewActivity.java`. MainActivity expects `Project/config.xml` and `Project/calibration_CB_Ex.log` below external storage. Camera capture uses NV21/YUV and Gray-code patterns. Historical reports say to recalibrate if the prism moves.

No original verified one-command build procedure was recovered. A historical build would need the separately obtained OpenCV Android library, support-library dependency and the missing application/calibration resources restored under appropriate terms. It would also need the original hardware/configuration for capture. This subset lacks binary/image assets, calibration/decode arrays and raw datasets; configuration/sample files were not fabricated to make it appear complete.

Excluded: OpenCV/support SDK binaries, APK/class outputs, original Git history, IDE user state, images and unreviewed reports. Source bytes are unchanged; no recovered code or binary was executed, and no successful reconstruction is claimed.

## Links

- [Project entry on Aaron Wetzler's website](https://twerdster.github.io/#3d-scanner-on-android)

## Attribution and Updates

The historical website lists Arkadi Godlin, Alex Kligman and Alon Zivrin. The final report identifies Alon Zvirin as the lab engineer; the website credit is retained without asserting he was a student. No blanket software license has been added. Dependencies retain their own terms. Original authors can open an issue to contribute updates or request corrections or removal of their material.

