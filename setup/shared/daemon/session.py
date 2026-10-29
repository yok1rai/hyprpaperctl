import os
import shlex

from .files import Operations, ServiceFile
from .models import Installation, Layout

VARIABLES = (
    "HOME", "USER", "LOGNAME", "PATH", "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME",
    "WAYLAND_DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE", "DBUS_SESSION_BUS_ADDRESS",
)


def capture_session(layout: Layout, operations: Operations):
    for name in ("XDG_RUNTIME_DIR", "HYPRLAND_INSTANCE_SIGNATURE", "WAYLAND_DISPLAY"):
        if not os.environ.get(name):
            raise ValueError(f"{name} is missing. Run this command inside Hyprland.")
    text = "".join(f"export {name}={shlex.quote(os.environ[name])}\n" for name in VARIABLES if name in os.environ)
    file = ServiceFile(layout.environment, text, 0o600)
    if operations.dry_run:
        print(f"Would capture session environment in {file.path}")
    else:
        operations.write(file)


def render_launcher(installation: Installation, layout: Layout) -> ServiceFile:
    q = shlex.quote
    log = ""
    if installation.manager == "runit":
        logs = layout.log_directory(installation)
        log = (
            f"mkdir -p {q(str(logs))}\n"
            f"exec >>{q(str(logs / 'output.log'))} 2>>{q(str(logs / 'error.log'))}\n"
        )
    text = (
        "#!/bin/sh\nset -eu\numask 077\n"
        f"if [ ! -r {q(str(layout.environment))} ]; then\n"
        "  echo 'Run setup/installd.py start inside Hyprland first.' >&2\n  exit 1\nfi\n"
        f". {q(str(layout.environment))}\n"
        ': "${XDG_RUNTIME_DIR:?Missing XDG_RUNTIME_DIR}"\n'
        ': "${HYPRLAND_INSTANCE_SIGNATURE:?Missing Hyprland session}"\n'
        f"{log}cd {q(installation.project)}\n"
        f"exec {q(installation.bun)} run {q(str(installation.project + '/hyprpaperd/daemon.ts'))} {q(installation.directory)}\n"
    )
    return ServiceFile(layout.launcher, text)
