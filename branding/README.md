# Manafe3 brand — logo concepts

Open `index.html` in a browser for the brand sheet (`preview.png` is a picture of it).

- `build-logos.mjs` draws every logo as geometry and writes `concepts/*.svg`:
  `node branding/build-logos.mjs`
- Six symbol concepts: A Tapered Frame, B M-Frame (chosen), C Nut & I-Section, D Isometric Bay, E Grid Bubble,
  F Seal — each as a symbol, a horizontal lockup, light and dark. A and B also have stacked and bilingual (منافع)
  versions; there is a wordmark-only version, app icons, an animated loader (tapered frames) and the red NOT FOR ISSUE stamp.
- The wordmark needs no font. The Arabic word and the small taglines use system fonts (Cairo / Segoe UI); outline them
  before sending files to a printer.
- **Chosen (2026-11-05): concept B, M-Frame** (it replaced A the same day). `build-logos.mjs` also writes the app's
  `devshell/site/favicon.svg` (the M-frame tile). After changing it, re-make the PNG and ICO: render the SVG at
  256 px on a transparent background (headless Edge, `--default-background-color=00000000`), then with Pillow save
  `favicon-32.png` (32 px) and `favicon.ico` (16, 32, 48 px).
