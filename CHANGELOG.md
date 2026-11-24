# Changelog

## 1.1.1

- Reopening Mod Manager fetches the mod list again when it's more than 5 minutes old, so newly added mods show up. The refresh button now says ⟳ Refresh.
- Remove from the list (in a mod's ⋯ menu): the person who added a mod, or the owner of its GitHub repo, can take it off the community list.
- To update a listing's name, description, side or tags, submit the mod again (same people as above).

## 1.1.0

- Modpacks are built in, with a new Modpacks tab. Keep mods in packs and choose which servers each pack loads on. The right mods are swapped in when the game starts. Based on Modpacks by Shadow.
- Add to pack: put any mod from the list straight into a pack.
- Server pack (server launcher): pick the mods players need, then share your server's address.
- Join a server's pack: enter a server's address, and Mod Manager downloads its mods and loads them only on that server. The first time you join a server that shares a pack, Mod Manager offers to set it up, and it updates on later joins.
- Safer downloads, from Sheikah Mods by Shadow: HTTPS uses a bundled, up-to-date certificate list, so PCs with an old certificate store still connect. Large mods (up to 512 MB) stream straight to disk. Packs download four mods at a time and show "Downloading 3 of 8". Link packs check every redirect.
- Fixed a rare launcher crash when a download started right after closing a window.

## 1.0.0 - first release

- Browse and search the community mod list, with client/server filters.
- One-click install, update, update all and uninstall from GitHub releases.
- Submit a mod from the launcher.
