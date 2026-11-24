# Changelog

## 1.1.1

- ⟳ Refresh always gets the newest list. Before, GitHub could hand out a copy up to 5 minutes old, so people saw different lists right after a mod was added. Reopening Mod Manager also refreshes a list that's more than 5 minutes old.
- Remove from the list (in a mod's ⋯ menu): the person who added a mod, or the owner of its GitHub repo, can take it off the community list.
- Edit listing (in a mod's ⋯ menu): change a listed mod's name, description, side or tags. Same people as above.
- The owner of the community list can edit or remove any listing.
- Scrolling fixes: searching or filtering after scrolling down no longer leaves a blank page. The Modpacks and Server pack tabs scroll when they're taller than the window, so their bottom buttons are always reachable. The mouse wheel scrolls whichever list is under the pointer.

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
