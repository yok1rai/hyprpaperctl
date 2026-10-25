import sys
import os
import shutil
import argparse
import subprocess
import platform
import tempfile
import time


# ============================================================
# Exceptions
# ============================================================

class VerErr(Exception):
    pass


class OsErr(Exception):
    pass


class PackageErr(Exception):
    pass


# ============================================================
# Colors
# ============================================================

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"


# ============================================================
# Constants
# ============================================================

MIN_PYTHON_VERSION = (3, 13)

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

SPINNER = [
    "⠋",
    "⠙",
    "⠹",
    "⠸",
    "⠼",
    "⠴",
    "⠦",
    "⠧",
    "⠇",
    "⠏",
]


# ============================================================
# Basic Utilities
# ============================================================

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


def is_root() -> bool:
    return os.geteuid() == 0


def privilege_prefix() -> list[str]:
    if is_root():
        return []

    if shutil.which("sudo") is None:
        raise OsErr(
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
        raise OsErr(
            "Root privileges are required, "
            "but sudo was not found."
        )

    try:
        subprocess.run(
            ["sudo", "-v"],
            check=True,
        )

    except subprocess.CalledProcessError:
        raise OsErr(
            "Could not acquire root privileges."
        )


def get_package_manager() -> str | None:
    for manager in SUPPORTED_PACKAGE_MANAGERS:
        if shutil.which(manager):
            return manager

    return None


# ============================================================
# Version Detection
# ============================================================

def get_hyprland_version() -> tuple[int, ...] | None:
    if shutil.which("hyprland") is None:
        return None

    try:
        result = subprocess.run(
            ["hyprland", "-v"],
            capture_output=True,
            text=True,
            check=True,
        )

        first_line = result.stdout.splitlines()[0]
        version = first_line.split()[1]

        return tuple(
            map(
                int,
                version.split("."),
            )
        )

    except (
        subprocess.CalledProcessError,
        IndexError,
        ValueError,
    ):
        return None


def get_hyprpaper_version() -> tuple[int, ...] | None:
    if shutil.which("hyprpaper") is None:
        return None

    try:
        result = subprocess.run(
            ["hyprpaper", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )

        version = (
            result.stdout
            .strip()
            .split()[-1]
            .lstrip("v")
        )

        return tuple(
            map(
                int,
                version.split("."),
            )
        )

    except (
        subprocess.CalledProcessError,
        IndexError,
        ValueError,
    ):
        return None


# ============================================================
# Status Output
# ============================================================

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


# ============================================================
# Command Execution
# ============================================================

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


# ============================================================
# Prerequisites
# ============================================================

def basic_requirements() -> str:
    """
    Requirements that must be valid even for `update`.

    Python version is intentionally NOT checked here.
    """

    if platform.system() != "Linux":
        raise OsErr(
            f"Unsupported operating system: "
            f"{platform.system()}. "
            "Linux is required."
        )

    package_manager = (
        get_package_manager()
    )

    if package_manager is None:
        raise PackageErr(
            "No supported package manager "
            "was found."
        )

    return package_manager


def prerequisites() -> str:
    """
    Full requirements for installing/running normally.
    """

    package_manager = (
        basic_requirements()
    )

    python_version = (
        get_python_version()
    )

    if (
        python_version
        < MIN_PYTHON_VERSION
    ):
        raise VerErr(
            f"Python "
            f"{format_version(MIN_PYTHON_VERSION)} "
            "or newer is required."
        )

    return package_manager


# ============================================================
# Pretend / Status
# ============================================================

def pretend() -> None:

    python_version = (
        get_python_version()
    )

    package_manager = (
        get_package_manager()
    )

    hyprland_installed = (
        shutil.which("hyprland")
        is not None
    )

    hyprpaper_installed = (
        shutil.which("hyprpaper")
        is not None
    )

    hyprland_version = (
        get_hyprland_version()
        if hyprland_installed
        else None
    )

    hyprpaper_version = (
        get_hyprpaper_version()
        if hyprpaper_installed
        else None
    )

    python_ok = (
        python_version
        >= MIN_PYTHON_VERSION
    )

    linux_ok = (
        platform.system()
        == "Linux"
    )

    package_ok = (
        package_manager
        is not None
    )

    print(
        "\nPrerequisites:"
    )

    print_status(
        (
            "Python Version "
            f"(min: "
            f"{format_version(MIN_PYTHON_VERSION)})"
        ),
        python_ok,
        format_version(
            python_version
        ),
    )

    print_status(
        "Supported OS",
        linux_ok,
        platform.system(),
    )

    print_status(
        "Supported Package Manager",
        package_ok,
        package_manager,
    )

    print(
        "\nInstallation Status:"
    )

    print_package_status(
        "Hyprland",
        hyprland_installed,
        hyprland_version,
    )

    print_package_status(
        "Hyprpaper",
        hyprpaper_installed,
        hyprpaper_version,
    )

    print()

    if (
        python_ok
        and linux_ok
        and package_ok
    ):
        print(
            f"{GREEN}"
            "All prerequisites are satisfied."
            f"{RESET}"
        )

    else:
        print(
            f"{RED}"
            "Some prerequisites are "
            "not satisfied."
            f"{RESET}"
        )

    print(
        f"\n{YELLOW}"
        "Run with `--help` "
        "to learn more."
        f"{RESET}"
    )


# ============================================================
# Install Command Generation
# ============================================================

def build_app_command(
    package_manager: str,
    app: str,
) -> list[str]:

    package = app.lower()

    # --------------------------------------------------------
    # Nix
    # --------------------------------------------------------

    if package_manager == "nix":
        return [
            "nix",
            "profile",
            "install",
            f"nixpkgs#{package}",
        ]

    root = privilege_prefix()

    # --------------------------------------------------------
    # Gentoo
    # --------------------------------------------------------

    if package_manager == "emerge":

        gentoo_package = {
            "Hyprland":
                "gui-wm/hyprland",

            "Hyprpaper":
                "gui-apps/hyprpaper",
        }[app]

        return [
            *root,
            "emerge",
            gentoo_package,
        ]

    # --------------------------------------------------------
    # Other distros
    # --------------------------------------------------------

    match package_manager:

        case "pacman":
            return [
                *root,
                "pacman",
                "-S",
                "--needed",
                "--noconfirm",
                package,
            ]

        case "apt":
            return [
                *root,
                "apt",
                "install",
                "-y",
                package,
            ]

        case "dnf":
            return [
                *root,
                "dnf",
                "install",
                "-y",
                package,
            ]

        case "zypper":
            return [
                *root,
                "zypper",
                "--non-interactive",
                "install",
                package,
            ]

        case "apk":
            return [
                *root,
                "apk",
                "add",
                package,
            ]

        case "xbps-install":
            return [
                *root,
                "xbps-install",
                "-y",
                package,
            ]

        case _:
            raise PackageErr(
                f"Unsupported package manager: "
                f"{package_manager}"
            )


def build_install_tasks(
    package_manager: str,
    install_hyprland: bool,
    install_hyprpaper: bool,
) -> list[tuple[str, list[str]]]:

    tasks = []

    # Current Gentoo Hypr packages are provided
    # through the Hypr overlay.
    if package_manager == "emerge":

        root = privilege_prefix()

        tasks += [
            (
                "Enable Hypr repository",
                [
                    *root,
                    "eselect",
                    "repository",
                    "enable",
                    "hyproverlay",
                ],
            ),
            (
                "Sync Hypr repository",
                [
                    *root,
                    "emaint",
                    "sync",
                    "-r",
                    "hyproverlay",
                ],
            ),
        ]

    if install_hyprland:
        tasks.append(
            (
                "Hyprland",
                build_app_command(
                    package_manager,
                    "Hyprland",
                ),
            )
        )

    if install_hyprpaper:
        tasks.append(
            (
                "Hyprpaper",
                build_app_command(
                    package_manager,
                    "Hyprpaper",
                ),
            )
        )

    return tasks


# ============================================================
# Update Command Generation
# ============================================================

def build_update_tasks(
    package_manager: str,
) -> list[tuple[str, list[str]]]:

    # --------------------------------------------------------
    # Nix
    # --------------------------------------------------------

    if package_manager == "nix":
        return [
            (
                "Nix profile",
                [
                    "nix",
                    "profile",
                    "upgrade",
                    "--all",
                ],
            ),
        ]

    root = privilege_prefix()

    # --------------------------------------------------------
    # Gentoo
    # --------------------------------------------------------

    if package_manager == "emerge":
        return [
            (
                "Enable Hypr repository",
                [
                    *root,
                    "eselect",
                    "repository",
                    "enable",
                    "hyproverlay",
                ],
            ),

            (
                "Repositories",
                [
                    *root,
                    "emaint",
                    "sync",
                    "-a",
                ],
            ),

            (
                "Python",
                [
                    *root,
                    "emerge",
                    "--update",
                    "dev-lang/python",
                ],
            ),

            (
                "Hyprland",
                [
                    *root,
                    "emerge",
                    "--update",
                    "gui-wm/hyprland",
                ],
            ),

            (
                "Hyprpaper",
                [
                    *root,
                    "emerge",
                    "--update",
                    "gui-apps/hyprpaper",
                ],
            ),
        ]

    # --------------------------------------------------------
    # Arch
    # --------------------------------------------------------

    if package_manager == "pacman":
        return [
            (
                "System packages",
                [
                    *root,
                    "pacman",
                    "-Syu",
                    "--noconfirm",
                ],
            ),

            (
                "Python",
                [
                    *root,
                    "pacman",
                    "-S",
                    "--needed",
                    "--noconfirm",
                    "python",
                ],
            ),

            (
                "Hyprland",
                [
                    *root,
                    "pacman",
                    "-S",
                    "--needed",
                    "--noconfirm",
                    "hyprland",
                ],
            ),

            (
                "Hyprpaper",
                [
                    *root,
                    "pacman",
                    "-S",
                    "--needed",
                    "--noconfirm",
                    "hyprpaper",
                ],
            ),
        ]

    # --------------------------------------------------------
    # Debian / Ubuntu
    # --------------------------------------------------------

    if package_manager == "apt":
        return [
            (
                "Repositories",
                [
                    *root,
                    "apt",
                    "update",
                ],
            ),

            (
                "Python",
                [
                    *root,
                    "apt",
                    "install",
                    "-y",
                    "python3",
                ],
            ),

            (
                "Hyprland",
                [
                    *root,
                    "apt",
                    "install",
                    "-y",
                    "hyprland",
                ],
            ),

            (
                "Hyprpaper",
                [
                    *root,
                    "apt",
                    "install",
                    "-y",
                    "hyprpaper",
                ],
            ),
        ]

    # --------------------------------------------------------
    # Fedora
    # --------------------------------------------------------

    if package_manager == "dnf":
        return [
            (
                "Repositories",
                [
                    *root,
                    "dnf",
                    "makecache",
                    "--refresh",
                    "-y",
                ],
            ),

            (
                "Python",
                [
                    *root,
                    "dnf",
                    "install",
                    "-y",
                    "python3",
                ],
            ),

            (
                "Hyprland",
                [
                    *root,
                    "dnf",
                    "install",
                    "-y",
                    "hyprland",
                ],
            ),

            (
                "Hyprpaper",
                [
                    *root,
                    "dnf",
                    "install",
                    "-y",
                    "hyprpaper",
                ],
            ),
        ]

    # --------------------------------------------------------
    # openSUSE
    # --------------------------------------------------------

    if package_manager == "zypper":
        return [
            (
                "Repositories",
                [
                    *root,
                    "zypper",
                    "--non-interactive",
                    "refresh",
                ],
            ),

            (
                "Python",
                [
                    *root,
                    "zypper",
                    "--non-interactive",
                    "install",
                    "python3",
                ],
            ),

            (
                "Hyprland",
                [
                    *root,
                    "zypper",
                    "--non-interactive",
                    "install",
                    "hyprland",
                ],
            ),

            (
                "Hyprpaper",
                [
                    *root,
                    "zypper",
                    "--non-interactive",
                    "install",
                    "hyprpaper",
                ],
            ),
        ]

    # --------------------------------------------------------
    # Alpine
    # --------------------------------------------------------

    if package_manager == "apk":
        return [
            (
                "Repositories",
                [
                    *root,
                    "apk",
                    "update",
                ],
            ),

            (
                "Python",
                [
                    *root,
                    "apk",
                    "add",
                    "--upgrade",
                    "python3",
                ],
            ),

            (
                "Hyprland",
                [
                    *root,
                    "apk",
                    "add",
                    "--upgrade",
                    "hyprland",
                ],
            ),

            (
                "Hyprpaper",
                [
                    *root,
                    "apk",
                    "add",
                    "--upgrade",
                    "hyprpaper",
                ],
            ),
        ]

    # --------------------------------------------------------
    # Void
    # --------------------------------------------------------

    if package_manager == "xbps-install":
        return [
            (
                "Repositories",
                [
                    *root,
                    "xbps-install",
                    "-S",
                ],
            ),

            (
                "Python",
                [
                    *root,
                    "xbps-install",
                    "-y",
                    "python3",
                ],
            ),

            (
                "Hyprland",
                [
                    *root,
                    "xbps-install",
                    "-y",
                    "hyprland",
                ],
            ),

            (
                "Hyprpaper",
                [
                    *root,
                    "xbps-install",
                    "-y",
                    "hyprpaper",
                ],
            ),
        ]

    raise PackageErr(
        f"Unsupported package manager: "
        f"{package_manager}"
    )


# ============================================================
# Install
# ============================================================

def install(
    force: bool = False,
    verbose: bool = False,
) -> None:

    package_manager = prerequisites()

    hyprland_installed = (
        shutil.which("hyprland")
        is not None
    )

    hyprpaper_installed = (
        shutil.which("hyprpaper")
        is not None
    )

    hyprland_version = (
        get_hyprland_version()
        if hyprland_installed
        else None
    )

    hyprpaper_version = (
        get_hyprpaper_version()
        if hyprpaper_installed
        else None
    )

    # --------------------------------------------------------
    # Already installed
    # --------------------------------------------------------

    if (
        hyprland_installed
        and hyprpaper_installed
    ):

        print_package_status(
            "Hyprland",
            True,
            hyprland_version,
        )

        print_package_status(
            "Hyprpaper",
            True,
            hyprpaper_version,
        )

        print(
            f"\n{GREEN}"
            "Hyprland and Hyprpaper "
            "are already installed."
            f"{RESET}"
        )

        return

    # --------------------------------------------------------
    # Information
    # --------------------------------------------------------

    print_package_status(
        "Hyprland",
        hyprland_installed,
        hyprland_version,
    )

    print_package_status(
        "Hyprpaper",
        hyprpaper_installed,
        hyprpaper_version,
    )

    if verbose:

        print(
            f"\nOperating System: "
            f"{platform.system()}"
        )

        print(
            f"Package Manager: "
            f"{package_manager}"
        )

        print(
            f"Python: "
            f"{format_version(get_python_version())}"
        )

    # --------------------------------------------------------
    # Confirmation
    # --------------------------------------------------------

    if not force:

        answer = input(
            "\nProceed with installation? "
            "[y/N] "
        ).strip().lower()

        if answer not in (
            "y",
            "yes",
        ):
            print(
                "Installation canceled."
            )

            return

    # --------------------------------------------------------
    # Build + execute
    # --------------------------------------------------------

    tasks = build_install_tasks(
        package_manager,
        install_hyprland=(
            not hyprland_installed
        ),
        install_hyprpaper=(
            not hyprpaper_installed
        ),
    )

    run_tasks(
        "Installing dependencies",
        tasks,
        verbose=verbose,
    )

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------

    hyprland_installed = (
        shutil.which("hyprland")
        is not None
    )

    hyprpaper_installed = (
        shutil.which("hyprpaper")
        is not None
    )

    if not hyprland_installed:
        raise PackageErr(
            "Hyprland could not be detected "
            "after installation."
        )

    if not hyprpaper_installed:
        raise PackageErr(
            "Hyprpaper could not be detected "
            "after installation."
        )

    print(
        f"{GREEN}"
        "Installation completed successfully."
        f"{RESET}"
    )


# ============================================================
# Update
# ============================================================

def update(
    force: bool = False,
    verbose: bool = False,
) -> None:

    # Deliberately doesn't enforce the current Python version.
    package_manager = basic_requirements()

    current_python = (
        get_python_version()
    )

    old_hyprland = (
        get_hyprland_version()
    )

    old_hyprpaper = (
        get_hyprpaper_version()
    )

    print(
        "\nCurrent versions:"
    )

    print(
        " Python: "
        f"{format_version(current_python)}"
    )

    print(
        " Hyprland: "
        + (
            format_version(old_hyprland)
            if old_hyprland is not None
            else "not installed / unknown"
        )
    )

    print(
        " Hyprpaper: "
        + (
            format_version(old_hyprpaper)
            if old_hyprpaper is not None
            else "not installed / unknown"
        )
    )

    if not force:

        answer = input(
            "\nUpdate repositories, Python, "
            "Hyprland and Hyprpaper? [y/N] "
        ).strip().lower()

        if answer not in (
            "y",
            "yes",
        ):
            print(
                "Update canceled."
            )

            return

    tasks = build_update_tasks(
        package_manager
    )

    run_tasks(
        "Updating dependencies",
        tasks,
        verbose=verbose,
    )

    # --------------------------------------------------------
    # Verify updated environment
    # --------------------------------------------------------

    system_python = (
        get_system_python_version()
    )

    hyprland_installed = (
        shutil.which("hyprland")
        is not None
    )

    hyprpaper_installed = (
        shutil.which("hyprpaper")
        is not None
    )

    new_hyprland = (
        get_hyprland_version()
        if hyprland_installed
        else None
    )

    new_hyprpaper = (
        get_hyprpaper_version()
        if hyprpaper_installed
        else None
    )

    print(
        "\nUpdate Status:"
    )

    if system_python is not None:

        print_status(
            (
                "Python "
                f"(min: "
                f"{format_version(MIN_PYTHON_VERSION)})"
            ),
            (
                system_python
                >= MIN_PYTHON_VERSION
            ),
            format_version(
                system_python
            ),
        )

    else:
        print_status(
            "Python",
            False,
            "version unknown",
        )

    print_package_status(
        "Hyprland",
        hyprland_installed,
        new_hyprland,
    )

    print_package_status(
        "Hyprpaper",
        hyprpaper_installed,
        new_hyprpaper,
    )

    if (
        system_python is None
        or system_python
        < MIN_PYTHON_VERSION
    ):
        raise VerErr(
            "The update completed, but "
            f"Python "
            f"{format_version(MIN_PYTHON_VERSION)}+ "
            "is still unavailable."
        )

    if not hyprland_installed:
        raise PackageErr(
            "The update completed, but "
            "Hyprland could not be detected."
        )

    if not hyprpaper_installed:
        raise PackageErr(
            "The update completed, but "
            "Hyprpaper could not be detected."
        )

    print(
        f"\n{GREEN}"
        "Update completed successfully."
        f"{RESET}"
    )

    # If Python itself changed, this process still uses
    # the interpreter it started with.
    if (
        system_python
        != current_python
    ):
        print(
            f"{YELLOW}"
            "Python was updated. "
            "Restart this script to use the "
            "new interpreter."
            f"{RESET}"
        )


# ============================================================
# Main
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hyprland / Hyprpaper dependency installer."
    )

    subparsers = parser.add_subparsers(
        dest="command",
    )



    install_parser = subparsers.add_parser(
        "install",
        help="Install Hyprland and Hyprpaper.",
    )

    install_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Skip confirmation prompts.",
    )

    install_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show package-manager output.",
    )

    update_parser = subparsers.add_parser(
        "update",
        help="Update prerequisites, Hyprland, and Hyprpaper.",
    )

    update_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Skip confirmation prompts.",
    )

    update_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show package-manager output.",
    )

    subparsers.add_parser(
        "pretend",
        help="Show dependency and installation status.",
    )

    args = parser.parse_args()

    try:

        match args.command:

            case "install":
                install(
                    force=args.force,
                    verbose=args.verbose,
                )

            case "update":
                update(
                    force=args.force,
                    verbose=args.verbose,
                )

            case "pretend":
                pretend()

            case None:
                print(
                    f"{YELLOW}"
                    "No command was provided. "
                    "Running in pretend mode."
                    f"{RESET}"
                )

                pretend()

    except (
        VerErr,
        OsErr,
        PackageErr,
    ) as error:

        restore_terminal()

        print(
            f"{RED}"
            f"Error: {error}"
            f"{RESET}",
            file=sys.stderr,
        )

        sys.exit(1)

    except KeyboardInterrupt:

        restore_terminal()

        print(
            f"\n{RED}"
            "Operation interrupted."
            f"{RESET}",
            file=sys.stderr,
        )

        sys.exit(130)


if __name__ == "__main__":
    main()
