from ..files import Operations, ServiceFile
from ..models import Installation, Layout


def quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%").replace("$", "$$") + '"'


class Systemd:
    tools = ("systemctl",)

    def __init__(self, installation: Installation, layout: Layout):
        self.installation = installation
        self.layout = layout
        self.system = installation.scope == "system"

    def files(self):
        identity = ""
        session = "PartOf=graphical-session.target\nAfter=graphical-session.target\n"
        if self.system:
            identity = f"User={self.installation.user}\nGroup={self.installation.group}\n"
            session = ""
        text = (
            f"[Unit]\nDescription=wallpaper daemon\n{session}\n"
            f"[Service]\nType=simple\n{identity}"
            f"ExecStart=/bin/sh {quote(str(self.layout.launcher))}\n"
            "StandardOutput=journal\nStandardError=journal\nSyslogIdentifier=wallpaperd\n"
            "Restart=on-failure\nRestartSec=3\nTimeoutStopSec=10\nUMask=0077\n"
        )
        return [ServiceFile(self.layout.service(self.installation), text, 0o644, self.system)]

    def control(self, action: str, operations: Operations):
        args = ["systemctl"]
        if not self.system:
            args.append("--user")
        args.append(action)
        if action != "daemon-reload":
            args.append("wallpaperd.service")
        operations.command(args, self.system)

    def installed(self, operations: Operations):
        self.control("daemon-reload", operations)

    def uninstall(self, operations: Operations):
        self.control("stop", operations)
        operations.remove(self.layout.service(self.installation), self.system)
        self.control("daemon-reload", operations)
