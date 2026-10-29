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
bun run start
```

Use `bun run dev` to restart automatically when source files change. The daemon entry point is currently a placeholder, so starting it exits without running a service.

Commit `bun.lock` when dependencies change. For a reproducible install, run `bun install --frozen-lockfile`.
