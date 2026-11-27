# Pesu Stickers

**© Karthik, all rights reserved, not for reuse.** These stickers are made for the Pesu
keyboard only. You may not copy, change, share or use them in any other app, sticker pack
or product. See [LICENSE](LICENSE).

Stickers for the Pesu keyboard. The keyboard downloads new and changed stickers from here,
so they update without a new app version.

## Add or change a sticker

1. Put the PNG in `source/`, named `<number>_<words>.png` (any size; a white background is made see-through automatically).
   - Same number as an existing sticker = replaces it (e.g. `013_thank_you.png`).
   - New number = new sticker (e.g. `328_good_vibes.png`).
   - A letter after the number = a version of that sticker, found by the same searches
     (e.g. `013a_nandri.png` shows up when someone searches "thank").
2. Commit. GitHub makes the 512×512 WebP files in `out/` and adds a line to `stickers.json`
   for any new number (takes about a minute; see the Actions tab).
3. Check the new line in `stickers.json`: fix the **caption** (punctuation like `!` or `?`),
   **category** (the page it shows on) and **tags** (extra search words, English or Tamil).

Phones pick up the changes within a day, or straight away with **Get new stickers** on the
Stickers tab.

## Numbers

`numbers.csv` lists every sticker's number, caption, page and file name (open it in Excel). New stickers can come in numbered above 350; they are given a free number and the list is updated.

## Hide a sticker

Add its number to `"hidden"` at the end of `stickers.json`, e.g. `"hidden": ["191", "051"]`.
It disappears from the keyboard, including the stickers built into the app.

## Pages (categories)

Everyday · Reactions · Love & Family · Wishes & Festivals · Support · Tamil · Office · Daily Life · Travel.
A new category name becomes a new page.

## Request a sticker (button in the app)

In `stickers.json`, the `requests` part controls the **Request a sticker** button in
Settings → Stickers:

- `form`: your Google Form's pre-filled link, made with **TEST-PHONE** in the Phone question and
  **TEST-VERSION** in the Pesu version question (Pesu puts the real values there).
- `enabled`: `true` shows the text and button, `false` hides them. Phones pick it up within a day.
