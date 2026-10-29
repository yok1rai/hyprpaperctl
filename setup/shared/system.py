"""Operating-system and privilege helpers."""

import os
import shutil
import subprocess

from .errors import OperatingSystemError


def is_root() -> bool:
    return os.geteuid() == 0


def privilege_prefix() -> list[str]:
    if is_root():
        return []

    if shutil.which("sudo") is None:
        raise OperatingSystemError(
            "Root privileges are required, "
            "but sudo was not found."
        )

    return ["sudo"]


def request_root_privileges() -> None:
    """
    Authenticate sudo before starting the quiet UI.

    This prevents an invisible password prompt while package
    manager output is hidden.
    """

    if is_root():
        return

    if shutil.which("sudo") is None:
        raise OperatingSystemError(
            "Root privileges are required, "
            "but sudo was not found."
        )

    try:
        subprocess.run(
            ["sudo", "-v"],
            check=True,
        )

    except subprocess.CalledProcessError:
        raise OperatingSystemError(
            "Could not acquire root privileges."
        )
