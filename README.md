# Pesu Stickers

Stickers for the Pesu keyboard. The keyboard downloads new and changed stickers from here,
so they update without a new app version.

## Add or change a sticker

1. Put the PNG in `source/`, named `<number>_<words>.png` (any size, transparent background).
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

## Hide a sticker

Add its number to `"hidden"` at the end of `stickers.json`, e.g. `"hidden": ["191", "051"]`.
It disappears from the keyboard, including the stickers built into the app.

## Pages (categories)

Everyday · Reactions · Love & Family · Wishes & Festivals · Support · Tamil · Office · Daily Life · Travel.
A new category name becomes a new page.
