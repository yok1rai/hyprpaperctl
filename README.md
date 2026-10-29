# HyprPaperCTL 

HyprPaperCtl aims for a good client to use hyprpaper 

**Requirements:** 

- hyprctl 
- hyprpaper 
- Linux
- Bun (installed automatically by the dependency installer)
- python 3.13 or above for installers 

Run `python setup/deps.py install --verbose` to install dependencies

Run `python setup/deps.py update --verbose` to update dependencies, including Bun.

For every supported package manager, Bun uses the [official installer](https://bun.com/docs/installation) to install the latest stable release into `$BUN_INSTALL` (default: `~/.bun`). Missing Bash, curl, and unzip prerequisites are installed through the system package manager. The update command refreshes this user-local Bun installation as well.

Development uses Bun to install dependencies and run TypeScript directly:

```sh
bun install
bun run typecheck
bun run start /path/to/wallpapers
```

Use `bun run dev /path/to/wallpapers` to restart automatically when source files change. Hyprland and hyprpaper must be running. The daemon listens on `/tmp/hyprpaperd.sock` and closes its socket and client connections on SIGINT or SIGTERM. An existing socket address causes startup to fail instead of replacing another daemon.

Commit `bun.lock` when dependencies change. For a reproducible install, run `bun install --frozen-lockfile`.
