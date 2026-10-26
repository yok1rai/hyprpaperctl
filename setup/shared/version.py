"""Version-related helpers."""

import shutil
import subprocess
import sys


def format_version(
    version: tuple[int, ...],
) -> str:
    return ".".join(map(str, version))


def get_python_version() -> tuple[int, ...]:
    """
    Version of the interpreter currently running this script.
    """

    return tuple(sys.version_info[:3])


def get_system_python_version() -> tuple[int, ...] | None:
    """
    Query Python again from PATH.

    Useful after updating Python because the currently running
    process still has the old sys.version_info.
    """

    executable = (
        shutil.which("python3")
        or shutil.which("python")
    )

    if executable is None:
        return None

    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            check=True,
        )

        output = (
            result.stdout.strip()
            or result.stderr.strip()
        )

        version = output.split()[1]

        return tuple(
            map(
                int,
                version.split(".")[:3],
            )
        )

    except (
        subprocess.CalledProcessError,
        IndexError,
        ValueError,
    ):
        return None
