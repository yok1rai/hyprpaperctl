"""Terminal cursor and line controls."""

import sys

HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR_LINE = "\033[2K"


def hide_cursor() -> None:
    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()


def restore_terminal() -> None:
    if sys.stdout.isatty():
        sys.stdout.write(
            SHOW_CURSOR
        )

        sys.stdout.flush()
