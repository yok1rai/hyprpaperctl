import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

from shared.daemon.files import Operations
from shared.daemon.installer import DaemonInstaller
from shared.daemon.models import MANAGERS, Installation, Layout, detect_manager


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install and manage the wallpaper daemon.")
    parser.add_argument("action", choices=("install", "uninstall", "start", "stop", "restart", "status", "supervise"))
    parser.add_argument("--manager", choices=MANAGERS)
    parser.add_argument("--scope", choices=("user", "system"), help="Installation scope (default: user).")
    parser.add_argument("--wallpaper-dir", type=Path)
    parser.add_argument("--bun", type=Path)
    parser.add_argument("--runit-service-dir", type=Path, default=Path("/var/service"), help="System runit's watched directory.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def layout_from_environment() -> Layout:
    config = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    if not config.is_absolute() or not state.is_absolute():
        raise ValueError("XDG_CONFIG_HOME and XDG_STATE_HOME must be absolute paths.")
    return Layout(config, state)


def installation_from_arguments(args: argparse.Namespace) -> Installation:
    if args.wallpaper_dir is None:
        raise ValueError("install requires --wallpaper-dir.")
    directory = args.wallpaper_dir.expanduser().resolve()
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")
    fallback = Path(os.environ.get("BUN_INSTALL", str(Path.home() / ".bun"))) / "bin/bun"
    bun = Path(args.bun or shutil.which("bun") or fallback).expanduser().resolve()
    if not bun.is_file() or not os.access(bun, os.X_OK):
        raise ValueError("Bun not found; install dependencies or pass --bun.")
    return Installation.create(
        args.manager or detect_manager(), args.scope or "user", directory, bun,
        Path(__file__).resolve().parent.parent, args.runit_service_dir.resolve(),
    )


def main() -> None:
    args = arguments()
    if sys.platform != "linux":
        raise ValueError("The daemon requires Linux.")
    if os.geteuid() == 0:
        raise ValueError("Run as your desktop user. System installations request sudo only for privileged operations.")
    installer = DaemonInstaller(layout_from_environment(), Operations(args.dry_run))
    match args.action:
        case "install":
            installation = installation_from_arguments(args)
        case _:
            installation = installer.load()
            if args.manager and args.manager != installation.manager:
                raise ValueError(f"Installed backend is {installation.manager}.")
            if args.scope and args.scope != installation.scope:
                raise ValueError(f"Installed scope is {installation.scope}.")
    installer.dispatch(args.action, installation)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
