"""Reusable command execution with quiet/verbose task UIs."""

import subprocess
import tempfile
import time

from .errors import PackageErr
from .system import request_root_privileges
from .ui import GREEN, RESET, SPINNER, YELLOW, draw_task_ui, restore_terminal


def command_failure(
    label: str,
    return_code: int,
    log_file,
) -> PackageErr:

    log_file.flush()
    log_file.seek(0)

    output = log_file.read().strip()

    if output:
        lines = output.splitlines()

        # Don't dump 500 package-manager lines.
        tail = "\n".join(
            lines[-15:]
        )

        return PackageErr(
            f"{label} failed with exit code "
            f"{return_code}.\n\n"
            f"Last output:\n{tail}"
        )

    return PackageErr(
        f"{label} failed with exit code "
        f"{return_code}."
    )


def run_verbose_command(
    label: str,
    command: list[str],
) -> None:

    print(
        f"\n{YELLOW}"
        f"[{label}]"
        f"{RESET}"
    )

    print(
        f"$ {' '.join(command)}"
    )

    try:
        subprocess.run(
            command,
            check=True,
        )

    except FileNotFoundError:
        raise PackageErr(
            f"Command not found: "
            f"{command[0]}"
        )

    except subprocess.CalledProcessError as error:
        raise PackageErr(
            f"{label} failed with exit code "
            f"{error.returncode}."
        )


def run_tasks(
    title: str,
    tasks: list[tuple[str, list[str]]],
    verbose: bool = False,
) -> None:

    if not tasks:
        return

    # --------------------------------------------------------
    # Verbose mode
    # --------------------------------------------------------

    if verbose:
        for label, command in tasks:
            run_verbose_command(
                label,
                command,
            )

        return

    # --------------------------------------------------------
    # Non-interactive terminal fallback
    # --------------------------------------------------------

    if not sys.stdout.isatty():

        for label, command in tasks:

            if (
                command
                and command[0] == "sudo"
            ):
                request_root_privileges()

            print(
                f"{label}..."
            )

            with tempfile.TemporaryFile(
                mode="w+"
            ) as log:

                try:
                    result = subprocess.run(
                        command,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        text=True,
                    )

                except FileNotFoundError:
                    raise PackageErr(
                        f"Command not found: "
                        f"{command[0]}"
                    )

                if result.returncode != 0:
                    raise command_failure(
                        label,
                        result.returncode,
                        log,
                    )

            print(
                f"{GREEN}✔ {label}{RESET}"
            )

        return

    # --------------------------------------------------------
    # Animated terminal UI
    # --------------------------------------------------------

    completed: set[str] = set()

    previous_lines = 0
    spinner_index = 0

    sys.stdout.write(
        "\033[?25l"
    )

    sys.stdout.flush()

    try:

        for label, command in tasks:

            if (
                command
                and command[0] == "sudo"
            ):
                request_root_privileges()

            with tempfile.TemporaryFile(
                mode="w+"
            ) as log:

                try:
                    process = subprocess.Popen(
                        command,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        text=True,
                    )

                except FileNotFoundError:
                    raise PackageErr(
                        f"Command not found: "
                        f"{command[0]}"
                    )

                while process.poll() is None:

                    previous_lines = draw_task_ui(
                        title=title,
                        tasks=tasks,
                        completed=completed,
                        current=label,
                        spinner=SPINNER[
                            spinner_index
                            % len(SPINNER)
                        ],
                        previous_lines=previous_lines,
                    )

                    spinner_index += 1

                    time.sleep(0.1)

                if process.returncode != 0:
                    raise command_failure(
                        label,
                        process.returncode,
                        log,
                    )

            completed.add(
                label
            )

            previous_lines = draw_task_ui(
                title=title,
                tasks=tasks,
                completed=completed,
                current=None,
                spinner="✔",
                previous_lines=previous_lines,
            )

    except KeyboardInterrupt:

        if (
            "process" in locals()
            and process.poll() is None
        ):
            process.terminate()

        raise

    finally:
        restore_terminal()

    print()
