# Cheetos Mod Manager

A Tavern launcher addon for finding, installing and updating A Township Tale mods in one click, no more copying DLLs around by hand. It works in both the **client** launcher (players) and the **server** launcher (server owners).

## What it does

- **Browse and search** the community mod list. Filter by mods for players, servers, or both.
- **Install** a mod with one click. Mod Manager downloads the mod's latest GitHub release and puts its files in the right place.
- **Update** mods when their authors publish a new release, one at a time or with **Update all**.
- **Uninstall** removes exactly the files Mod Manager installed. Mods you installed by hand are never touched, and if a mod would replace one of your files, Mod Manager asks first.
- **Submit a mod**: share your own mod by pasting its GitHub link. Your browser opens a pre-filled form, and the mod appears in the list a few minutes after its checks pass.

> Listed mods are submitted by the community and aren't reviewed. Mods run code on your PC, so only install mods you trust.

## Install

1. Download `CheetosModManager-<version>.zip` from the latest release.
2. Extract the `mod_manager` folder into your launcher's `addons` folder.
3. Enable **Cheetos Mod Manager** in the launcher's addon list and restart the launcher.
4. Open it with the **🧩 Mod Manager** button.

MelonLoader must be installed first. Use the launcher's own Mods window for that.

## For mod authors

Your mod needs a public GitHub repo with a release that has your `.dll` attached, or a `.zip` with the `.dll` inside. Inside a zip, files in `Mods`, `Plugins` or `UserLibs` folders go into the matching game folder. Any other `.dll` goes into `Mods`. If a release has both `.dll` files and a `.zip`, the `.dll` files are used.

The list lives at [Cheeto35/ATTModIndex](https://github.com/Cheeto35/ATTModIndex). New releases are picked up within an hour.

## Files it keeps

- `<game folder>/.mod_manager.json`: which mods are installed and which files belong to each.
- In the launcher's data folder: `mod_manager_index_cache.json`, a saved copy of the list for when you're offline, and `mod_manager_settings.json`.

Made By Cheeto.
