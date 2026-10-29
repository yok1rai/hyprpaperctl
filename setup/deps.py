import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from shared.colors import GREEN, RED, YELLOW
from shared.errors import OperatingSystemError, PackageError, VersionError
from shared.packages import get_package_manager
from shared.process import run_tasks
from shared.styles import RESET
from shared.system import privilege_prefix
from shared.terminal import restore_terminal
from shared.ui import print_package_status, print_status
from shared.version import (
    format_version, get_python_version, get_system_python_version,
)


MIN_PYTHON_VERSION = (3, 13)


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


def expose_bun() -> None:
    """Make the installer's user-local Bun visible in this process."""
    bun_bin = Path(os.environ.get("BUN_INSTALL", str(Path.home() / ".bun"))) / "bin"
    if (bun_bin / "bun").is_file():
        os.environ["PATH"] = str(bun_bin) + os.pathsep + os.environ.get("PATH", "")


def build_bun_tasks(package_manager: str) -> list[tuple[str, list[str]]]:
    """Install the latest stable Bun with its official user-local installer."""
    tasks = [
        (f"Bun prerequisite: {package}", build_app_command(package_manager, package))
        for package in ("bash", "curl", "unzip")
        if shutil.which(package) is None
    ]
    tasks.append((
        "Bun",
        ["bash", "-o", "pipefail", "-c", "curl -fsSL https://bun.com/install | bash"],
    ))
    return tasks


def get_bun_version() -> tuple[int, ...] | None: 
    expose_bun()
    if shutil.which("bun") is None: 
        return None 

    try: 
        result = subprocess.run(
            ["bun", "--version"],
            capture_output=True, 
            text=True, 
            check=True
        ) 

        version = (result
            .stdout
            .strip() 
            .split(".")
        )

        return tuple(
            map(
                int, 
                version
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

def basic_requirements() -> str:
    """
    Requirements that must be valid even for `update`.

    Python version is intentionally NOT checked here.
    """

    if platform.system() != "Linux":
        raise OperatingSystemError(
            f"Unsupported operating system: "
            f"{platform.system()}. "
            "Linux is required."
        )

    package_manager = (
        get_package_manager()
    )

    if package_manager is None:
        raise PackageError(
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
        raise VersionError(
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

    expose_bun()

    bun_installed = (
        shutil.which("bun")
        is not None 
    )

    bun_version = get_bun_version() 

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

    print_package_status("Bun", bun_installed, bun_version)

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
            "bash": "app-shells/bash",
            "curl": "net-misc/curl",
            "unzip": "app-arch/unzip",

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
            raise PackageError(
                f"Unsupported package manager: "
                f"{package_manager}"
            )


def build_install_tasks(
    package_manager: str,
    install_hyprland: bool,
    install_hyprpaper: bool,
    install_bun: bool = True,
) -> list[tuple[str, list[str]]]:

    tasks = []

    # Current Gentoo Hypr packages are provided
    # through the Hypr overlay.
    if package_manager == "emerge" and (install_hyprland or install_hyprpaper):

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

    if install_bun:
        tasks.extend(build_bun_tasks(package_manager))

    return tasks


# ============================================================
# Update Command Generation
# ============================================================

def _build_system_update_tasks(
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

    raise PackageError(
        f"Unsupported package manager: "
        f"{package_manager}"
    )


def build_update_tasks(package_manager: str) -> list[tuple[str, list[str]]]:
    return _build_system_update_tasks(package_manager) + build_bun_tasks(package_manager)


# ============================================================
# Install
# ============================================================

def install(
    force: bool = False,
    verbose: bool = False,
) -> None:

    package_manager = prerequisites()

    expose_bun()
    bun_installed = shutil.which("bun") is not None
    bun_version = get_bun_version()

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
        and bun_installed
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

        print_package_status("Bun", True, bun_version)

        print(
            f"\n{GREEN}"
            "Hyprland, Hyprpaper and Bun "
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

    print_package_status("Bun", bun_installed, bun_version)

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
        install_bun=not bun_installed,
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

    expose_bun()
    if shutil.which("bun") is None:
        raise PackageError("Bun could not be detected after installation.")

    if not hyprland_installed:
        raise PackageError(
            "Hyprland could not be detected "
            "after installation."
        )

    if not hyprpaper_installed:
        raise PackageError(
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

    old_bun = get_bun_version()

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

    print(" Bun: " + (format_version(old_bun) if old_bun is not None else "not installed / unknown"))

    if not force:

        answer = input(
            "\nUpdate repositories, Python, "
            "Hyprland, Hyprpaper and Bun? [y/N] "
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

    expose_bun()
    bun_installed = shutil.which("bun") is not None
    new_bun = get_bun_version()

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

    print_package_status("Bun", bun_installed, new_bun)
    if not bun_installed:
        raise PackageError("The update completed, but Bun could not be detected.")

    if (
        system_python is None
        or system_python
        < MIN_PYTHON_VERSION
    ):
        raise VersionError(
            "The update completed, but "
            f"Python "
            f"{format_version(MIN_PYTHON_VERSION)}+ "
            "is still unavailable."
        )

    if not hyprland_installed:
        raise PackageError(
            "The update completed, but "
            "Hyprland could not be detected."
        )

    if not hyprpaper_installed:
        raise PackageError(
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
        description="Hyprland / Hyprpaper / Bun dependency installer."
    )

    subparsers = parser.add_subparsers(
        dest="command",
    )



    install_parser = subparsers.add_parser(
        "install",
        help="Install Hyprland, Hyprpaper, and Bun.",
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
        help="Update prerequisites, Hyprland, Hyprpaper, and Bun.",
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
        VersionError,
        OperatingSystemError,
        PackageError,
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

