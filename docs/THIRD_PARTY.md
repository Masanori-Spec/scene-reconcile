# Dependencies and provenance

The standalone application contains original JavaScript/CSS/HTML and requires no runtime network dependency. No OBS binary or source code is bundled with the product. OBS is a separate, GPL-licensed native consumer used only in hosted verification from its official release asset. The harness follows official APIs and native-format behavior; it does not incorporate OBS implementation source.

Development dependencies are pinned in package-lock.json:

- esbuild 0.25.11, MIT, build-only
- @playwright/test 1.56.0, Apache-2.0, browser-test-only
- Python standard library, semantic oracle and packaging

The hosted native gate installs Ubuntu packages for Xvfb, Openbox, xdotool, Tesseract, ImageMagick, WebSocket client and DejaVu fonts from the Ubuntu package registry. Official OBS package dependencies are resolved by apt. No system browser security setting is changed, no software from an unrecognized source is installed, and no user-owned device or configuration is accessed.

No new project license or rights grant is declared by this prototype.
