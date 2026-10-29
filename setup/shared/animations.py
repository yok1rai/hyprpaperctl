"""Spinner frames and task progress rendering."""

import sys

from .colors import GREEN, YELLOW
from .styles import RESET
from .terminal import CLEAR_LINE

SPINNER_FRAMES = (
    "⠋", "⠙", "⠹", "⠸", "⠼",
    "⠴", "⠦", "⠧", "⠇", "⠏",
)


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
            f"{CLEAR_LINE}{line}\n"
        )

    sys.stdout.flush()

    return len(lines)
