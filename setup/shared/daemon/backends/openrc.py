import shlex

from ..files import Operations, ServiceFile
from ..models import Installation, Layout


class OpenRC:
    tools = ("rc-service", "openrc-run", "supervise-daemon")

    def __init__(self, installation: Installation, layout: Layout):
        self.installation = installation
        self.layout = layout
        self.system = installation.scope == "system"

    def files(self):
        identity = ""
        pidfile = '"${XDG_RUNTIME_DIR}/wallpaperd.pid"'
        if self.system:
            identity = f"command_user={shlex.quote(self.installation.user + ':' + self.installation.group)}\n"
            pidfile = '"/run/wallpaperd.pid"'
        logs = self.layout.log_directory(self.installation)
        text = (
            "#!/sbin/openrc-run\n"
            'description="wallpaper daemon"\n'
            'supervisor="supervise-daemon"\n'
            'command="/bin/sh"\n'
            f"command_args_foreground={shlex.quote(shlex.quote(str(self.layout.launcher)))}\n"
            f"{identity}pidfile={pidfile}\n"
            f"output_log={shlex.quote(shlex.quote(str(logs / 'output.log')))}\n"
            f"error_log={shlex.quote(shlex.quote(str(logs / 'error.log')))}\n"
            'respawn_delay="30"\n'
        )
        return [ServiceFile(self.layout.service(self.installation), text, 0o755, self.system)]

    def control(self, action: str, operations: Operations):
        args = ["rc-service"]
        if not self.system:
            args.append("--user")
        operations.command([*args, "wallpaperd", action], self.system)

    def installed(self, operations: Operations):
        logs = self.layout.log_directory(self.installation)
        if self.system:
            if logs.is_symlink():
                raise ValueError(f"Log directory must not be a symlink: {logs}")
            operations.command(["install", "-d", "-m", "755", str(logs)], True)
        elif not operations.dry_run:
            logs.mkdir(parents=True, exist_ok=True, mode=0o700)

    def uninstall(self, operations: Operations):
        self.control("stop", operations)
        operations.remove(self.layout.service(self.installation), self.system)
