# Cheetos Mod Manager

A Tavern launcher addon for finding, installing and updating A Township Tale mods in one click, no more copying DLLs around by hand. It works in both the **client** launcher (players) and the **server** launcher (server owners).

## What it does

- **Browse and search** the community mod list. Filter by mods for players, servers, or both.
- **Install** a mod with one click. Mod Manager downloads the mod's latest GitHub release and puts its files in the right place.
- **Update** mods when their authors publish a new release, one at a time or with **Update all**.
- **Uninstall** removes exactly the files Mod Manager installed. Mods you installed by hand are never touched, and if a mod would replace one of your files, Mod Manager asks first.
- **Submit a mod**: share your own mod by pasting its GitHub link. Your browser opens a pre-filled form, and the mod appears in the list a few minutes after its checks pass.

> Listed mods are submitted by the community and aren't reviewed. Mods run code on your PC, so only install mods you trust.

## Modpacks (players)

The **Modpacks** tab keeps your mods in packs. Each pack is Off, On everywhere, or On only for the servers you pick. When the game starts, Mod Manager puts exactly the right mods in `Mods` for the server you're joining, so servers that need different mods just work.

- **Join a server's pack…**: type a server's address, like `play.example.com:1757`. Mod Manager asks the server which mods it uses, downloads them into a pack, and loads that pack only on that server. When the server owner changes the pack, you get the changes the next time you join.
- The first time you join a server that shares a pack, Mod Manager asks "This server has a modpack. Set it up and play?"
- **Add to pack**, in any mod's ⋯ menu, puts a mod from the list straight into one of your packs.
- Packs from a link (a server's `manifest.json`), zip import and export, and per-mod ticks all work as they did in Modpacks.

## Server pack (server owners)

In the server launcher, the **Server pack** tab lists the mods you've installed that players need too. Tick the ones players should get, add any other mod from the list or any direct `.dll` download link, and press **Save**. Copy the share line and post it with your server. Players can also just join: Mod Manager offers your pack automatically.

The pack is shared through the launcher's login port (1762), the same one players already connect to, so you don't need a website. Players get exactly the files and links you list.

## Install

1. Download `CheetosModManager-<version>.zip` from the latest release.
2. Extract the `mod_manager` folder into your launcher's `addons` folder.
3. Enable **Cheetos Mod Manager** in the launcher's addon list and restart the launcher.
4. Open it with the **🧩 Mod Manager** button.

If you used the separate Modpacks addon, turn it off: Mod Manager includes it now and uses the same `Modpacks` folder, so your packs carry over.

MelonLoader must be installed first. Use the launcher's own Mods window for that.

## For mod authors

Your mod needs a public GitHub repo with a release that has your `.dll` attached, or a `.zip` with the `.dll` inside. Inside a zip, files in `Mods`, `Plugins` or `UserLibs` folders go into the matching game folder. Any other `.dll` goes into `Mods`. If a release has both `.dll` files and a `.zip`, the `.dll` files are used.

The list lives at [Cheeto35/ATTModIndex](https://github.com/Cheeto35/ATTModIndex). New releases are picked up within an hour.

## Downloads

Every download uses HTTPS certificates checked against a bundled copy of Mozilla's trusted list (`modpacks/cacert.pem`, from [certifi](https://pypi.org/project/certifi/) 2026.11.20, MPL-2.0, see `modpacks/CERTIFI-LICENSE`), so a PC with an out-of-date certificate store still connects. If that check fails, your PC's own list gets one try. If both fail, Mod Manager says so and asks you to check your PC's date and time.

Files stream straight to disk, up to 512 MB each and 512 MB per update. Packs download up to four mods at a time. Files from a pack link must stay on that link's site through every redirect.

## Files it keeps

- `<game folder>/.mod_manager.json`: which mods are installed and which files belong to each.
- In the launcher's data folder: `mod_manager_index_cache.json`, a saved copy of the list for when you're offline, and `mod_manager_settings.json`.

## Credits

Modpacks is by **Shadow** ([calebv2/-Client-Addon-Modpacks](https://github.com/calebv2/-Client-Addon-Modpacks)) and is included under the MIT licence (see `modpacks/LICENSE`). The download code (`modpacks/tls.py`) is adapted from Shadow's **Sheikah Mods** ([calebv2/Sheikah-Mods](https://github.com/calebv2/Sheikah-Mods)), also MIT. Mod Manager adds server packs, Add to pack, and the combined window.

Made By Cheeto.
