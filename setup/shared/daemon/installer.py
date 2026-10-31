import json
from pathlib import Path
import shutil
import subprocess

from .backends import backend
from .files import Operations, ServiceFile
from .models import Installation, Layout
from .session import capture_session, render_launcher


class DaemonInstaller:
    def __init__(self, layout: Layout, operations: Operations):
        self.layout = layout
        self.operations = operations

    def load(self) -> Installation:
        try:
            value = json.loads(self.layout.settings.read_text())
        except (OSError, ValueError) as error:
            raise ValueError("No valid installation metadata; run installd.py install first.") from error
        return Installation.from_dict(value)

    def install(self, installation: Installation):
        service = backend(installation, self.layout)
        if self.layout.settings.exists():
            raise ValueError("A service is already installed. Uninstall it before reinstalling.")
        for value in (*installation.to_dict().values(), str(self.layout.config_home), str(self.layout.root)):
            if any(character in value for character in ("\0", "\r", "\n")):
                raise ValueError("Paths and service settings cannot contain newlines or NUL characters.")
        files = [render_launcher(installation, self.layout), *service.files()]
        for file in files:
            if file.path.exists() or file.path.is_symlink():
                raise ValueError(f"Refusing to replace existing file: {file.path}")
        if installation.manager == "runit" and installation.scope == "system":
            active = Path(installation.runit_active)
            if not active.is_dir():
                raise ValueError("Runit active directory not found; pass --runit-service-dir.")
            link = active / "wallpaperd"
            if link.exists() or link.is_symlink():
                raise ValueError(f"Service already registered: {link}")
        if not self.operations.dry_run:
            for tool in service.tools:
                if shutil.which(tool) is None:
                    raise ValueError(f"Required service tool not found: {tool}")
            self.layout.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        metadata = json.dumps(installation.to_dict(), indent=2) + "\n"
        files.append(ServiceFile(self.layout.settings, metadata, 0o600))
        written = []
        try:
            for file in files:
                self.operations.write(file)
                written.append(file)
            service.installed(self.operations)
        except (OSError, ValueError, subprocess.CalledProcessError):
            for file in reversed(written):
                try:
                    self.operations.remove(file.path, file.system)
                except (OSError, subprocess.CalledProcessError) as error:
                    print(f"Could not clean up {file.path}: {error}")
            raise
        print("Installation prepared. Start it from your Hyprland session after hyprpaper is running.")

    def uninstall(self, installation: Installation):
        backend(installation, self.layout).uninstall(self.operations)
        for path in (self.layout.launcher, self.layout.environment, self.layout.settings):
            self.operations.remove(path)

    def dispatch(self, action: str, installation: Installation):
        service = backend(installation, self.layout)
        match action:
            case "install":
                self.install(installation)
            case "uninstall":
                self.uninstall(installation)
            case "start" | "restart":
                capture_session(self.layout, self.operations)
                service.control(action, self.operations)
            case "stop" | "status":
                service.control(action, self.operations)
            case "supervise":
                if installation.manager != "runit" or installation.scope != "user":
                    raise ValueError("supervise requires a runit user installation.")
                capture_session(self.layout, self.operations)
                service.supervise(self.operations)
            case _:
                raise ValueError(f"Unknown installer action: {action}")
