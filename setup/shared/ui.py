"""Terminal status messages."""

import sys

from .colors import GREEN, RED
from .styles import RESET
from .version import format_version


def print_status(
    name: str,
    success: bool,
    extra: str | None = None,
) -> None:

    if success:
        message = (
            f" {GREEN}{name}: ✔"
        )
    else:
        message = (
            f" {RED}{name}: ✘"
        )

    if extra is not None:
        message += f" ({extra})"

    print(
        f"{message}{RESET}",
        file=(
            sys.stdout
            if success
            else sys.stderr
        ),
    )


def print_package_status(
    name: str,
    installed: bool,
    version: tuple[int, ...] | None,
) -> None:

    if not installed:
        print_status(
            f"{name} is not installed",
            False,
        )

        return

    if version is None:
        print_status(
            name,
            True,
            "version unknown",
        )

        return

    print_status(
        name,
        True,
        format_version(version),
    )
