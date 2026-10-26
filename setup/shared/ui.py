"""Small ANSI terminal UI helpers."""

import sys

from .version import format_version

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"

SPINNER = [
    "⠋", "⠙", "⠹", "⠸", "⠼",
    "⠴", "⠦", "⠧", "⠇", "⠏",
]


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


# ============================================================
# Terminal UI
# ============================================================

def progress_bar(
    percent: int,
    width: int = 30,
) -> str:

    filled = int(
        width * percent / 100
    )

    return (
        "["
        + "█" * filled
        + "─" * (width - filled)
        + "]"
    )


def draw_task_ui(
    title: str,
    tasks: list[tuple[str, list[str]]],
    completed: set[str],
    current: str | None,
    spinner: str,
    previous_lines: int,
) -> int:

    total = len(tasks)

    if total == 0:
        percent = 100
    else:
        percent = int(
            len(completed)
            / total
            * 100
        )

    labels = [
        label
        for label, _ in tasks
    ]

    lines = [
        f"{YELLOW}{title}{RESET}",
        "",
        (
            f" {progress_bar(percent)} "
            f"{percent:3d}%"
        ),
        "",
    ]

    for label in labels:

        if label in completed:
            lines.append(
                f" {GREEN}✔{RESET} "
                f"{label}"
            )

        elif label == current:
            lines.append(
                f" {YELLOW}{spinner}{RESET} "
                f"{label}"
            )

        else:
            lines.append(
                f" • {label}"
            )

    lines += [
        "",
        (
            f" Current: "
            f"{current or 'Finished'}"
        ),
    ]

    if previous_lines > 0:
        sys.stdout.write(
            f"\033[{previous_lines}F"
        )

    for line in lines:
        sys.stdout.write(
            f"\033[2K{line}\n"
        )

    sys.stdout.flush()

    return len(lines)


def restore_terminal() -> None:
    if sys.stdout.isatty():
        sys.stdout.write(
            "\033[?25h"
        )

        sys.stdout.flush()
