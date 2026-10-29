import os
from pathlib import Path
import shlex
import shutil

from ..files import Operations, ServiceFile
from ..models import Installation, Layout


class Runit:
    tools = ("sv", "runsv", "runsvdir", "chpst")

    def __init__(self, installation: Installation, layout: Layout):
        self.installation = installation
        self.layout = layout
        self.system = installation.scope == "system"
        self.service = layout.service(installation).parent
        self.link = Path(installation.runit_active) / "hyprpaperd"

    def files(self):
        command = f"/bin/sh {shlex.quote(str(self.layout.launcher))}"
        if self.system:
            identity = shlex.quote(self.installation.user + ":" + self.installation.group)
            command = f"chpst -u {identity} {command}"
        return [
            ServiceFile(self.service / "run", f"#!/bin/sh\nexec 2>&1\nexec {command}\n", 0o755, self.system),
            ServiceFile(self.service / "down", "", 0o644, self.system),
        ]

    def installed(self, operations: Operations):
        if self.system:
            operations.command(["ln", "-s", "--", str(self.service), str(self.link)], True)

    def control(self, action: str, operations: Operations):
        if not operations.dry_run and not (self.service / "supervise/ok").exists():
            raise ValueError("No runit supervisor is watching the service. Start the user supervisor or check --runit-service-dir.")
        match action:
            case "start" | "restart":
                operations.remove(self.service / "down", self.system)
                verb = "up" if action == "start" else "restart"
            case "stop":
                operations.write(ServiceFile(self.service / "down", "", 0o644, self.system))
                verb = "down"
            case "status":
                verb = "status"
            case _:
                raise ValueError(f"Unsupported runit action: {action}")
        operations.command(["sv", verb, str(self.service)], self.system)

    def supervise(self, operations: Operations):
        if self.system:
            raise ValueError("System runit services use the system supervisor; use start.")
        executable = shutil.which("runsvdir")
        if executable is None:
            raise ValueError("runsvdir is not installed.")
        operations.remove(self.service / "down")
        args = [executable, "-P", str(self.service.parent)]
        if operations.dry_run:
            operations.command(args)
        else:
            os.execv(executable, args)

    def uninstall(self, operations: Operations):
        supervised = (self.service / "supervise/ok").exists()
        if supervised or operations.dry_run:
            self.control("stop", operations)
        if self.system:
            operations.remove(self.link, True)
        else:
            removed = self.layout.root / "runit-uninstall"
            if removed.exists():
                raise ValueError(f"Remove leftover uninstall directory first: {removed}")
            print(f"Move {self.service} outside the supervisor directory")
            if not operations.dry_run:
                self.service.rename(removed)
            if supervised or operations.dry_run:
                operations.command(["sv", "exit", str(removed)])
            if not operations.dry_run:
                shutil.rmtree(removed)
            return
        for file in self.files():
            operations.remove(file.path, file.system)
