# Manafe3 brand — logo concepts

Open `index.html` in a browser for the brand sheet (`preview.png` is a picture of it).

- `build-logos.mjs` draws every logo as geometry and writes `concepts/*.svg`:
  `node branding/build-logos.mjs`
- Six symbol concepts: A Tapered Frame (recommended), B M-Frame, C Nut & I-Section, D Isometric Bay, E Grid Bubble,
  F Seal — each as a symbol, a horizontal lockup, light and dark. Concept A also has stacked, bilingual (منافع) and
  wordmark-only versions, app icons, an animated loader, and the red NOT FOR ISSUE stamp.
- The wordmark needs no font. The Arabic word and the small taglines use system fonts (Cairo / Segoe UI); outline them
  before sending files to a printer.
- **Chosen (2026-11-05): concept A, Tapered Frame.** `build-logos.mjs` also writes the app's `devshell/site/favicon.svg`
  (the small tile, without the rear bays, for 16-22 px). After changing it, re-make the PNG and ICO: render the SVG at
  256 px on a transparent background (headless Edge, `--default-background-color=00000000`), then with Pillow save
  `favicon-32.png` (32 px) and `favicon.ico` (16, 32, 48 px).
