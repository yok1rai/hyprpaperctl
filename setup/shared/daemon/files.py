from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import subprocess
import tempfile


@dataclass(frozen=True)
class ServiceFile:
    path: Path
    text: str
    mode: int = 0o700
    system: bool = False


class Operations:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def command(self, args: list[str], system: bool = False):
        if system:
            args = ["sudo", "--", *args]
        print(shlex.join(args), flush=True)
        if not self.dry_run:
            subprocess.run(args, check=True)

    def write(self, file: ServiceFile):
        print(f"Write {file.path} ({file.mode:o})")
        if self.dry_run:
            print(file.text)
            return
        if file.system:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf8") as temporary:
                temporary.write(file.text)
                temporary.flush()
                self.command(["install", "-D", "-m", f"{file.mode:o}", temporary.name, str(file.path)], True)
            return
        file.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=file.path.parent, prefix=".wallpaper-")
        try:
            with os.fdopen(descriptor, "w", encoding="utf8") as stream:
                os.fchmod(stream.fileno(), file.mode)
                stream.write(file.text)
            Path(temporary).replace(file.path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def remove(self, path: Path, system: bool = False):
        if system:
            self.command(["rm", "-f", "--", str(path)], True)
        else:
            print(f"Remove {path}")
            if not self.dry_run:
                path.unlink(missing_ok=True)
