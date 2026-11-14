# Related iOS Fusion renderer fragment

`viewer/FusionRenderer.mm` is a byte-for-byte recovery of one source file from a separate `Fusion` directory in the same historical Beam backup. Its header credits Rom Herskovitz (8 August 2014) and retains “Copyright (c) 2014 Technion. All rights reserved.” No license is added.

It performs OpenGL ES depth/volume rendering and ICP-related processing. Companion `FusionRenderer.h`, `Shaders.h`, `Consts.h`, application setup and depth data are absent from this recovered subset. The source is not independently buildable. Its association with the Beam backup does not establish that it captures or decodes Galaxy Beam structured-light patterns.

The original Xcode project is omitted because it carries personal signing configuration and references missing components. No SDK/framework binaries or datasets are included. See the [manifest](../../recovery/manifest.json) and [recovery notes](../../docs/RECOVERY.md).
