import os
import sys
import shutil
import subprocess

# Define separate dependency profiles for Desktop and Android
DESKTOP_PROFILE = {
    "name": "Desktop",
    "dependencies": [
        "pydantic==2.13.4",
        "pydantic-settings==2.14.2",
        "pyyaml==6.0.3",
        "fastapi==0.139.2",
        "uvicorn==0.51.0",
        "rich==15.0.0",
        "watchdog==6.0.0",
        "httpx==0.28.1",
        "typer==0.27.0",
        "click==8.1.8",
        "python-dotenv==1.2.2",
        "mcp>=1.28.1",
    ],
    "install_args": []
}

ANDROID_PROFILE = {
    "name": "Android",
    "dependencies": [
        "pydantic==2.13.4",
        "pydantic-settings==2.14.2",
        "pyyaml==6.0.3",
        "fastapi==0.139.2",
        "uvicorn==0.51.0",
        "rich==15.0.0",
        "watchdog==6.0.0",
        "httpx==0.28.1",
        "typer==0.27.0",
        "click==8.1.8",
        "python-dotenv==1.2.2",
        "mcp>=1.28.1",
    ],
    "install_args": [
        "--only-binary=pydantic-core",
        "--extra-index-url", "https://eutalix.github.io/android-pydantic-core/"
    ]
}

ANDROID_FALLBACK_PROFILE = {
    "name": "Android-Fallback",
    "dependencies": [
        "pyyaml==6.0.3",
        "fastapi==0.99.1",
        "uvicorn==0.51.0",
        "rich==15.0.0",
        "watchdog==6.0.0",
        "httpx==0.28.1",
        "typer==0.27.0",
        "click==8.1.8",
        "python-dotenv==1.2.2",
        "pydantic<2",
    ],
    "install_args": []
}

def detect_platform() -> str:
    # Safely import detect_platform from config
    try:
        from shadow.core.config import detect_platform as config_detect
        return config_detect()
    except ImportError:
        # Fallback inline detection if config is not importable
        if os.path.exists("/data/data/com.termux/files/usr") or "TERMUX_VERSION" in os.environ:
            return "Android / Termux"
        elif hasattr(sys, "getandroidapilevel") or "ANDROID_ROOT" in os.environ or "ANDROID_DATA" in os.environ:
            return "Android Python"
        elif sys.platform == "darwin":
            return "macOS"
        elif sys.platform == "win32":
            return "Windows"
        elif sys.platform.startswith("linux"):
            return "Linux"
        return sys.platform.capitalize() or "Unknown"

def is_android_platform() -> bool:
    plat = detect_platform()
    return "Android" in plat or "Termux" in plat

def validate_profile_compatibility(profile: dict, python_bin: str = None, use_uv: bool = None) -> tuple[bool, str]:
    """
    Validates compatibility of a dependency profile by running a dry-run install command.
    Returns (is_compatible, diagnostic_message).
    """
    if python_bin is None:
        python_bin = sys.executable
    if use_uv is None:
        use_uv = shutil.which("uv") is not None

    cmd = []
    if use_uv:
        cmd = ["uv", "pip", "install", "--dry-run", "--python", python_bin]
    else:
        cmd = [python_bin, "-m", "pip", "install", "--dry-run"]

    cmd.extend(profile["install_args"])
    cmd.extend(profile["dependencies"])

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if result.returncode == 0:
            return True, "Compatible"
        else:
            err_msg = result.stderr or result.stdout or "Unknown package resolution error"
            return False, f"Resolution failed with: {err_msg.strip()}"
    except Exception as e:
        return False, f"Failed to execute package manager dry-run: {str(e)}"

def filter_unsupported_dependencies(profile: dict, python_bin: str, use_uv: bool) -> dict:
    """
    Filters out dependencies from a profile that are unsupported on the current platform.
    On Android, if a package fails its individual dry-run, it is skipped.
    """
    is_android = is_android_platform()
    if not is_android:
        return profile

    filtered_deps = []
    for dep in profile["dependencies"]:
        cmd = []
        if use_uv:
            cmd = ["uv", "pip", "install", "--dry-run", "--python", python_bin]
        else:
            cmd = [python_bin, "-m", "pip", "install", "--dry-run"]

        cmd.extend(profile["install_args"])
        cmd.append(dep)

        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            if result.returncode == 0:
                filtered_deps.append(dep)
            else:
                print(f"[!] Android compatibility check: Skipping unsupported package '{dep}' (Dry-run failed: {result.stderr.strip() or result.stdout.strip()})")
        except Exception as e:
            print(f"[!] Android compatibility check: Skipping unsupported package '{dep}' due to execution error: {str(e)}")

    return {**profile, "dependencies": filtered_deps}

def choose_and_validate_profile(python_bin: str = None, use_uv: bool = None) -> tuple[dict, str]:
    """
    Chooses the correct dependency profile automatically and validates compatibility before installation.
    If Android, first attempts ANDROID_PROFILE. If incompatible, attempts ANDROID_FALLBACK_PROFILE.
    If Desktop, attempts DESKTOP_PROFILE.
    Returns (selected_profile, diagnostic_message).
    Raises Exception if no compatible profile can be found.
    """
    is_android = is_android_platform()
    plat = detect_platform()
    print(f"[*] Detecting platform: {plat} (is_android: {is_android})")

    if python_bin is None:
        python_bin = sys.executable
    if use_uv is None:
        use_uv = shutil.which("uv") is not None

    if is_android:
        # Filter standard Android profile dependencies first
        filtered_android_profile = filter_unsupported_dependencies(ANDROID_PROFILE, python_bin, use_uv)
        # 1. Try standard Android profile (Pydantic v2 with custom wheel index)
        compat_v2, reason_v2 = validate_profile_compatibility(filtered_android_profile, python_bin, use_uv)
        if compat_v2:
            return filtered_android_profile, f"Selected Android profile (Pydantic v2 compatible wheel verified on {plat})"

        # Filter Android Fallback profile dependencies first
        filtered_fallback_profile = filter_unsupported_dependencies(ANDROID_FALLBACK_PROFILE, python_bin, use_uv)
        # 2. Try Android Fallback profile (Pydantic v1)
        compat_v1, reason_v1 = validate_profile_compatibility(filtered_fallback_profile, python_bin, use_uv)
        if compat_v1:
            return filtered_fallback_profile, f"Selected Android-Fallback profile (Pydantic v1) because standard Android (Pydantic v2) wheel is incompatible: {reason_v2}"

        # If neither is supported, abort
        raise RuntimeError(
            f"Unsupported platform diagnostic: Neither Android profile nor Fallback profile could be resolved on {plat}.\n"
            f"V2 Error: {reason_v2}\n"
            f"V1 Fallback Error: {reason_v1}"
        )
    else:
        # Desktop Platform
        compat, reason = validate_profile_compatibility(DESKTOP_PROFILE, python_bin, use_uv)
        if compat:
            return DESKTOP_PROFILE, f"Selected Desktop profile on {plat}"
        else:
            raise RuntimeError(
                f"Unsupported platform diagnostic: Desktop profile could not be validated on {plat}.\n"
                f"Error: {reason}"
            )

def install_compatible_profile(python_bin: str = None, use_uv: bool = None) -> bool:
    """
    Detects, validates, and installs the correct compatible profile.
    Aborts with a clear diagnostic if a dependency set is unsupported on the current platform.
    """
    if python_bin is None:
        python_bin = sys.executable
    if use_uv is None:
        use_uv = shutil.which("uv") is not None

    profile, diagnostic = choose_and_validate_profile(python_bin, use_uv)
    print(f"[*] {diagnostic}")
    print(f"[*] Installing dependency profile: {profile['name']}...")

    # Build install command
    cmd = []
    if use_uv:
        cmd = ["uv", "pip", "install", "--python", python_bin]
    else:
        cmd = [python_bin, "-m", "pip", "install"]

    cmd.extend(profile["install_args"])
    cmd.extend(profile["dependencies"])

    # Run installation
    subprocess.run(cmd, check=True)

    # Get repo dir relative to this file's location to ensure -e . runs correctly from any cwd
    dependencies_file = os.path.abspath(__file__)
    core_dir = os.path.dirname(dependencies_file)
    shadow_dir = os.path.dirname(core_dir)
    repo_dir = os.path.dirname(shadow_dir)

    # Install editable package without deps
    editable_cmd = []
    if use_uv:
        editable_cmd = ["uv", "pip", "install", "--python", python_bin, "--no-deps", "-e", "."]
    else:
        editable_cmd = [python_bin, "-m", "pip", "install", "--no-deps", "-e", "."]

    subprocess.run(editable_cmd, cwd=repo_dir, check=True)
    print(f"[✓] Successfully installed {profile['name']} profile.")
    return True
