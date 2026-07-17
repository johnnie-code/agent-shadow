#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import venv
from pathlib import Path

def print_step(msg):
    print(f"\n[\033[1;32m*\033[0m] {msg}")

def print_error(msg):
    print(f"[\033[1;31mERROR\033[0m] {msg}", file=sys.stderr)

def print_warn(msg):
    print(f"[\033[1;33mWARNING\033[0m] {msg}")

def main():
    print("=" * 60)
    print("      PROJECT SHADOW — NATIVE SYSTEM-WIDE INSTALLER")
    print("=" * 60)

    # 1. Define Paths
    shadow_home = Path.home() / ".shadow"
    venv_dir = shadow_home / "venv"
    config_dir = shadow_home / "config"
    memory_dir = shadow_home / "memory"
    logs_dir = shadow_home / "logs"
    cache_dir = shadow_home / "cache"
    plugins_dir = shadow_home / "plugins"
    backups_dir = shadow_home / "backups"

    # 2. Create Layout
    print_step("Creating production-grade directory layout under ~/.shadow/...")
    for d in [shadow_home, config_dir, memory_dir, logs_dir, cache_dir, plugins_dir, backups_dir]:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  Created {d}")

    # 3. Copy/Create mission.md
    print_step("Setting up mission.md context file...")
    target_mission = shadow_home / "mission.md"
    source_mission = Path(__file__).parent / "mission.md"
    if target_mission.exists():
        print(f"  Existing mission.md detected at {target_mission}. Keeping intact.")
    elif source_mission.exists():
        shutil.copy(source_mission, target_mission)
        print(f"  Copied default mission.md to {target_mission}")
    else:
        # Create a default template if none exists
        default_content = """# Identity
Shadow User.

# Long-Term Goals
- Master Advanced Systems Engineering
- Deploy Autonomous Agent Networks

# Current Projects
- PROJECT SHADOW Core System

# Skills To Learn
- Python, Systems Architecting, Android Automation
"""
        target_mission.write_text(default_content, encoding="utf-8")
        print(f"  Created new default mission.md at {target_mission}")

    # 4. Create Isolated Virtual Environment
    print_step("Creating isolated virtual environment in ~/.shadow/venv/...")
    try:
        builder = venv.EnvBuilder(with_pip=True, clear=False)
        builder.create(venv_dir)
        print(f"  Virtual environment created/verified at {venv_dir}")
    except Exception as e:
        print_error(f"Failed to create virtual environment: {e}")
        sys.exit(1)

    # 5. Install Shadow and Dependencies
    print_step("Installing Shadow-OS package inside the virtual environment...")

    # Identify pip and python in the new venv
    venv_python = venv_dir / "bin" / "python"
    venv_pip = venv_dir / "bin" / "pip"

    if os.name == "nt":
        venv_python = venv_dir / "Scripts" / "python.exe"
        venv_pip = venv_dir / "Scripts" / "pip.exe"

    if not venv_python.exists():
        print_error(f"Virtual environment python executable not found at {venv_python}")
        sys.exit(1)

    # We try to use uv if available for speed, otherwise fall back to pip
    use_uv = False
    uv_path = shutil.which("uv")
    if uv_path:
        use_uv = True
        print("  Detected uv package manager. Using uv for fast installation.")

    src_dir = Path(__file__).parent.resolve()

    try:
        if use_uv:
            cmd = [uv_path, "pip", "install", "--python", str(venv_python), "-e", str(src_dir)]
        else:
            cmd = [str(venv_pip), "install", "-e", str(src_dir)]

        print(f"  Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        print("  Shadow-OS and dependencies successfully installed.")
    except Exception as e:
        print_error(f"Failed to install package: {e}")
        sys.exit(1)

    # 6. Expose Global Executable Launcher
    print_step("Creating global executable launcher...")

    prefix = os.environ.get("PREFIX")
    bin_dirs = []
    if prefix:
        bin_dirs.append(Path(prefix) / "bin")

    termux_usr_bin = Path("/data/data/com.termux/files/usr/bin")
    usr_local_bin = Path("/usr/local/bin")
    home_local_bin = Path.home() / ".local" / "bin"

    bin_dirs.extend([termux_usr_bin, usr_local_bin, home_local_bin])

    launcher_path = None
    for b_dir in bin_dirs:
        try:
            b_dir.mkdir(parents=True, exist_ok=True)
            test_file = b_dir / ".shadow_write_test"
            test_file.touch()
            test_file.unlink()
            launcher_path = b_dir / "shadow"
            break
        except Exception:
            continue

    if not launcher_path:
        launcher_path = shadow_home / "shadow"
        print_warn(f"Could not find a writable system-wide bin directory. Creating launcher in {launcher_path}")
    else:
        print(f"  Selected launcher path: {launcher_path}")

    # Generate launcher content
    if os.name == "nt":
        launcher_content = f"""@echo off
set SHADOW_HOME={shadow_home}
"{venv_python}" -m shadow.cli.main %*
"""
        launcher_path = launcher_path.with_suffix(".bat")
    else:
        launcher_content = f"""#!/bin/sh
# PROJECT SHADOW — Autonomous OS Control Terminal CLI
export SHADOW_HOME="{shadow_home}"
exec "{venv_python}" -m shadow.cli.main "$@"
"""

    try:
        launcher_path.write_text(launcher_content, encoding="utf-8")
        if os.name != "nt":
            launcher_path.chmod(0o755)
        print(f"  Launcher successfully written and made executable at: {launcher_path}")
    except Exception as e:
        print_error(f"Failed to write launcher executable: {e}")
        sys.exit(1)

    # 7. Shell Integration & Autocomplete
    print_step("Configuring shell autocompletes...")

    shell_rcs = [
        Path.home() / ".bashrc",
        Path.home() / ".zshrc",
        Path.home() / ".config" / "fish" / "config.fish"
    ]

    path_export_line = f'export PATH="$PATH:{launcher_path.parent}"'

    for rc in shell_rcs:
        if rc.exists() or rc.parent.exists():
            rc.parent.mkdir(parents=True, exist_ok=True)
            content = ""
            if rc.exists():
                content = rc.read_text(encoding="utf-8")

            if str(launcher_path.parent) not in content and launcher_path.parent != Path("/usr/bin") and launcher_path.parent != Path("/usr/local/bin"):
                print(f"  Adding PATH export to {rc}...")
                with rc.open("a", encoding="utf-8") as f:
                    f.write(f"\n# PROJECT SHADOW CLI PATH\n{path_export_line}\n")

            try:
                shell_name = "bash" if "bash" in rc.name else "zsh" if "zsh" in rc.name else "fish"
                subprocess.run([str(launcher_path), f"--install-completion", shell_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"  Installed tab-completion for {shell_name} in {rc.name}")
            except Exception:
                pass

    # 8. Initialize Database
    print_step("Initializing SQLite Database...")
    try:
        subprocess.run([str(venv_python), "-c", "from shadow.core.database import init_db; init_db()"], check=True)
        print("  Database initialized successfully.")
    except Exception as e:
        print_error(f"Failed to initialize database: {e}")

    # 9. Verification
    print_step("Verifying Shadow installation...")
    try:
        res = subprocess.run([str(launcher_path), "status"], capture_output=True, text=True)
        if res.returncode == 0:
            print("  Verification Succeeded! Output of 'shadow status':")
            for line in res.stdout.splitlines():
                print(f"    {line}")
        else:
            print_warn(f"CLI ran but returned exit code {res.returncode}. Error:\n{res.stderr}")
    except Exception as e:
        print_error(f"Failed to verify executable launcher: {e}")

    print("\n" + "=" * 60)
    print("      SHADOW-OS NATIVE SYSTEM-WIDE INSTALLATION COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    main()
