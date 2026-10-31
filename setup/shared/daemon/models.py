from dataclasses import asdict, dataclass
import grp
import os
from pathlib import Path
import pwd
import shutil

MANAGERS = ("systemd", "openrc", "runit")


def detect_manager() -> str:
    match True:
        case _ if Path("/run/systemd/system").is_dir() and shutil.which("systemctl"):
            return "systemd"
        case _ if Path("/run/openrc").exists() and shutil.which("rc-service"):
            return "openrc"
        case _ if shutil.which("runsvdir") and shutil.which("sv"):
            return "runit"
        case _:
            raise ValueError("Cannot detect service manager; pass --manager.")


@dataclass(frozen=True)
class Installation:
    manager: str
    scope: str
    user: str
    group: str
    project: str
    bun: str
    directory: str
    runit_active: str = "/var/service"

    @classmethod
    def create(cls, manager: str, scope: str, directory: Path, bun: Path, project: Path, runit_active: Path):
        account = pwd.getpwuid(os.getuid())
        return cls(manager, scope, account.pw_name, grp.getgrgid(account.pw_gid).gr_name,
                   str(project), str(bun), str(directory), str(runit_active))

    @classmethod
    def from_dict(cls, value: object):
        if not isinstance(value, dict):
            raise ValueError("Invalid installation metadata.")
        try:
            installation = cls(**value)
        except TypeError as error:
            raise ValueError("Installation metadata is outdated; reinstall the service.") from error
        if installation.manager not in MANAGERS or installation.scope not in ("user", "system"):
            raise ValueError("Invalid service manager or scope.")
        if installation.user != pwd.getpwuid(os.getuid()).pw_name:
            raise ValueError("Installation belongs to a different user.")
        return installation

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Layout:
    config_home: Path
    state_home: Path

    @property
    def root(self):
        return self.state_home / "wallpaper"

    @property
    def settings(self):
        return self.root / "service.json"

    @property
    def launcher(self):
        return self.root / "launch"

    @property
    def environment(self):
        return self.root / "session.env"

    def log_directory(self, installation: Installation) -> Path:
        if installation.manager == "openrc" and installation.scope == "system":
            return Path("/var/log/wallpaperd")
        return self.root / "logs"

    def service(self, installation: Installation) -> Path:
        match installation.manager, installation.scope:
            case "systemd", "system":
                return Path("/etc/systemd/system/wallpaperd.service")
            case "systemd", "user":
                return self.config_home / "systemd/user/wallpaperd.service"
            case "openrc", "system":
                return Path("/etc/init.d/wallpaperd")
            case "openrc", "user":
                return self.config_home / "rc/init.d/wallpaperd"
            case "runit", "system":
                return Path("/etc/sv/wallpaperd/run")
            case "runit", "user":
                return self.root / "runit/wallpaperd/run"
            case _:
                raise ValueError("Unsupported service manager or scope.")
