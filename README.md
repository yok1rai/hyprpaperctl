# wallpaper

wallpaper aims for a good client to use hyprpaper

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

Use `bun run dev /path/to/wallpapers` to restart automatically when source files change. Hyprland and hyprpaper must be running. The daemon listens on `/tmp/wallpaperd.sock` and closes its socket and client connections on SIGINT or SIGTERM. An existing socket address causes startup to fail instead of replacing another daemon.

Commit `bun.lock` when dependencies change. For a reproducible install, run `bun install --frozen-lockfile`.

Daemon installation supports systemd, OpenRC, and runit, with separate user and system scopes. Install project dependencies first with `bun install`.

```sh
python setup/installd.py install --manager openrc --scope system \
  --wallpaper-dir "$HOME/Pictures/Wallpapers"
```

Run the installer as your desktop user. For system scope, it invokes sudo only to install system files and control the service. The daemon runs as that desktop user, including when managed by a system service.

| Manager | System service                           | User service                                       |
| ------- | ---------------------------------------- | -------------------------------------------------- |
| systemd | `/etc/systemd/system/wallpaperd.service` | `$XDG_CONFIG_HOME/systemd/user/wallpaperd.service` |
| OpenRC  | `/etc/init.d/wallpaperd`                 | `$XDG_CONFIG_HOME/rc/init.d/wallpaperd`            |
| runit   | `/etc/sv/wallpaperd/run`                 | `$XDG_STATE_HOME/wallpaper/runit/wallpaperd/run`   |

The XDG defaults are `~/.config` and `~/.local/state`. Omitting `--scope` selects user scope; omitting `--manager` detects the service manager. `--bun /path/to/bun` selects a specific executable. `--dry-run` previews all files and commands without writes or sudo.

System runit installation registers a symlink in `/var/service` and initially keeps the service down. For distributions using another watched directory, supply it explicitly:

```sh
python setup/installd.py install --manager runit --scope system \
  --runit-service-dir /run/runit/service \
  --wallpaper-dir "$HOME/Pictures/Wallpapers"
```

Installations record the absolute checkout and Bun paths, so keep those paths available. Existing service files are preserved rather than overwritten. Only one installation is tracked per desktop user. Uninstall before changing managers or scopes.

After hyprpaper is running inside Hyprland:

```sh
python setup/installd.py start
python setup/installd.py status
python setup/installd.py restart
python setup/installd.py stop
python setup/installd.py uninstall
```

Later commands read the recorded manager and scope. `start` and `restart` capture the current session environment in a private `session.env` file; services need `XDG_RUNTIME_DIR`, `WAYLAND_DISPLAY`, and `HYPRLAND_INSTANCE_SIGNATURE` to communicate with Hyprland. Installation does not start the daemon or enable it at boot.

For a runit **user** installation, first run `python setup/installd.py supervise` inside Hyprland. This runs the user supervisor in the foreground. Use the lifecycle commands from another terminal and stop the service before ending the supervisor. System runit installations use the existing system supervisor and do not need this command.

To start with Hyprland, add an `exec-once` entry using absolute paths, after arranging for hyprpaper to be running:

```text
exec-once = /usr/bin/python3 /absolute/path/to/wallpaper/setup/installd.py start
```

Use `supervise` instead of `start` for runit user scope. OpenRC user scope requires a version supporting `--user` and an initialized OpenRC user session. The service formats follow the [OpenRC service guide](https://github.com/OpenRC/openrc/blob/master/service-script-guide.md), [systemd service documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html), and [runit user service documentation](https://www.smarden.org/runit/faq).

Daemon output destinations are explicit:

| Backend              | Standard output                             | Standard error                             |
| -------------------- | ------------------------------------------- | ------------------------------------------ |
| systemd, both scopes | Journal (`StandardOutput=journal`)          | Journal (`StandardError=journal`)          |
| OpenRC, system       | `/var/log/wallpaperd/output.log`            | `/var/log/wallpaperd/error.log`            |
| OpenRC, user         | `$XDG_STATE_HOME/wallpaper/logs/output.log` | `$XDG_STATE_HOME/wallpaper/logs/error.log` |
| runit, both scopes   | `$XDG_STATE_HOME/wallpaper/logs/output.log` | `$XDG_STATE_HOME/wallpaper/logs/error.log` |

OpenRC uses `output_log` and `error_log` in its generated service script. Runit redirects the daemon output after switching to the desktop user. Its supervisor's own messages still go to the supervisor output. The default state directory is `~/.local/state`. Logs are kept on uninstall.

For systemd, read logs with `journalctl --user -u wallpaperd.service -f` in user scope or `sudo journalctl -u wallpaperd.service -f` in system scope. Installation and session data stay under `$XDG_STATE_HOME/wallpaper`, even in system scope.

## Automatic wallpaper rotation

The daemon advances every monitor to the next wallpaper every 300 seconds by default.
It follows the loaded filename order and wraps from the last wallpaper to the first.
With no wallpaper selected, the first tick selects the first image. Empty lists are
skipped; a single selected image is left in place. Failed changes are logged and
retried on the next tick without preventing other monitors from advancing.

Control rotation through the CLI (also available in REPL mode):

```sh
bun run wallpapercli/index.ts auto-continue       # Show status
bun run wallpapercli/index.ts auto-continue 60    # Advance every 60 seconds
bun run wallpapercli/index.ts auto-continue off   # Disable rotation
```

Intervals must be whole seconds from 1 to 2147483. Changes restart the timer and
apply to all monitors. Settings last until daemon shutdown; restarting restores
the 300-second default. Manual wallpaper changes determine the next image without
resetting the timer. The next tick uses refreshed lists and directory changes.
