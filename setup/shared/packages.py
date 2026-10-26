"""Package-manager discovery helpers."""

import shutil

SUPPORTED_PACKAGE_MANAGERS = [
    "emerge",
    "apt",
    "dnf",
    "pacman",
    "zypper",
    "apk",
    "xbps-install",
    "nix",
]


def get_package_manager() -> str | None:
    for manager in SUPPORTED_PACKAGE_MANAGERS:
        if shutil.which(manager):
            return manager

    return None
