import os
import sys
import pytest
import subprocess
from unittest.mock import patch, MagicMock
from shadow.core.dependencies import (
    DESKTOP_PROFILE,
    ANDROID_PROFILE,
    ANDROID_FALLBACK_PROFILE,
    detect_platform,
    is_android_platform,
    validate_profile_compatibility,
    choose_and_validate_profile,
    install_compatible_profile
)

def test_detect_platform_and_is_android():
    # Test macOS
    with patch("sys.platform", "darwin"), patch("os.path.exists", return_value=False), patch("os.environ", {}):
        assert detect_platform() == "macOS"
        assert is_android_platform() is False

    # Test Windows
    with patch("sys.platform", "win32"), patch("os.path.exists", return_value=False), patch("os.environ", {}):
        assert detect_platform() == "Windows"
        assert is_android_platform() is False

    # Test Linux
    with patch("sys.platform", "linux"), patch("os.path.exists", return_value=False), patch("os.environ", {}):
        assert detect_platform() == "Linux"
        assert is_android_platform() is False

    # Test Termux
    with patch("os.path.exists", lambda path: True if "com.termux" in path else False), patch("os.environ", {}):
        assert detect_platform() == "Android / Termux"
        assert is_android_platform() is True

    # Test Android Python Env (non-Termux)
    with patch("os.path.exists", return_value=False), patch("os.environ", {"ANDROID_ROOT": "/system"}):
        assert detect_platform() == "Android Python"
        assert is_android_platform() is True

@patch("subprocess.run")
def test_validate_profile_compatibility_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="Success")
    is_compat, msg = validate_profile_compatibility(DESKTOP_PROFILE, use_uv=True)
    assert is_compat is True
    assert msg == "Compatible"
    assert "uv" in mock_run.call_args[0][0]

@patch("subprocess.run")
def test_validate_profile_compatibility_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stderr="Failed to resolve dependencies")
    is_compat, msg = validate_profile_compatibility(DESKTOP_PROFILE, use_uv=False)
    assert is_compat is False
    assert "Failed to resolve dependencies" in msg
    assert "pip" in mock_run.call_args[0][0] or "python" in mock_run.call_args[0][0]

@patch("shadow.core.dependencies.is_android_platform")
@patch("shadow.core.dependencies.detect_platform")
@patch("shadow.core.dependencies.validate_profile_compatibility")
def test_choose_and_validate_profile_desktop(mock_compat, mock_detect, mock_is_android):
    mock_is_android.return_value = False
    mock_detect.return_value = "Linux"
    mock_compat.return_value = (True, "Compatible")

    profile, diagnostic = choose_and_validate_profile()
    assert profile["name"] == "Desktop"
    assert "Selected Desktop profile" in diagnostic

@patch("shadow.core.dependencies.is_android_platform")
@patch("shadow.core.dependencies.detect_platform")
@patch("shadow.core.dependencies.validate_profile_compatibility")
def test_choose_and_validate_profile_desktop_unsupported(mock_compat, mock_detect, mock_is_android):
    mock_is_android.return_value = False
    mock_detect.return_value = "Linux"
    mock_compat.return_value = (False, "Dry-run failed")

    with pytest.raises(RuntimeError) as exc:
        choose_and_validate_profile()
    assert "Unsupported platform diagnostic" in str(exc.value)

@patch("shadow.core.dependencies.is_android_platform")
@patch("shadow.core.dependencies.detect_platform")
@patch("shadow.core.dependencies.validate_profile_compatibility")
@patch("shadow.core.dependencies.filter_unsupported_dependencies")
def test_choose_and_validate_profile_android_v2(mock_filter, mock_compat, mock_detect, mock_is_android):
    mock_is_android.return_value = True
    mock_detect.return_value = "Android / Termux"
    mock_filter.side_effect = lambda profile, *args, **kwargs: profile
    # Compatible with standard Android profile (Pydantic v2)
    mock_compat.return_value = (True, "Compatible")

    profile, diagnostic = choose_and_validate_profile()
    assert profile["name"] == "Android"
    assert "Selected Android profile" in diagnostic

@patch("shadow.core.dependencies.is_android_platform")
@patch("shadow.core.dependencies.detect_platform")
@patch("shadow.core.dependencies.validate_profile_compatibility")
@patch("shadow.core.dependencies.filter_unsupported_dependencies")
def test_choose_and_validate_profile_android_fallback(mock_filter, mock_compat, mock_detect, mock_is_android):
    mock_is_android.return_value = True
    mock_detect.return_value = "Android / Termux"
    mock_filter.side_effect = lambda profile, *args, **kwargs: profile

    # Side effect: ANDROID_PROFILE fails, ANDROID_FALLBACK_PROFILE succeeds
    def compat_side_effect(prof, *args, **kwargs):
        if prof["name"] == "Android":
            return False, "pydantic-core wheel not found"
        return True, "Compatible"

    mock_compat.side_effect = compat_side_effect

    profile, diagnostic = choose_and_validate_profile()
    assert profile["name"] == "Android-Fallback"
    assert "Selected Android-Fallback profile" in diagnostic
    assert "wheel is incompatible" in diagnostic

@patch("shadow.core.dependencies.is_android_platform")
@patch("shadow.core.dependencies.detect_platform")
@patch("shadow.core.dependencies.validate_profile_compatibility")
@patch("shadow.core.dependencies.filter_unsupported_dependencies")
def test_choose_and_validate_profile_android_unsupported(mock_filter, mock_compat, mock_detect, mock_is_android):
    mock_is_android.return_value = True
    mock_detect.return_value = "Android / Termux"
    mock_filter.side_effect = lambda profile, *args, **kwargs: profile
    mock_compat.return_value = (False, "Dry-run failed")

    with pytest.raises(RuntimeError) as exc:
        choose_and_validate_profile()
    assert "Neither Android profile nor Fallback profile could be resolved" in str(exc.value)

@patch("subprocess.run")
@patch("shadow.core.dependencies.choose_and_validate_profile")
def test_install_compatible_profile_success(mock_choose, mock_run):
    mock_choose.return_value = (DESKTOP_PROFILE, "Selected Desktop profile")
    mock_run.return_value = MagicMock(returncode=0)

    success = install_compatible_profile(use_uv=True)
    assert success is True
    # Two runs: one for dependencies, one for editable package
    install_calls = [call for call in mock_run.call_args_list if "install" in str(call)]
    assert len(install_calls) == 2

@patch("subprocess.run")
@patch("shadow.core.dependencies.is_android_platform")
def test_filter_unsupported_dependencies_android(mock_is_android, mock_run):
    mock_is_android.return_value = True

    # Let some package fail and some succeed
    # Let's say "mcp>=1.28.1" fails
    def run_side_effect(cmd, *args, **kwargs):
        # cmd has the dependency package at the end
        dep = cmd[-1]
        if "mcp" in dep:
            return MagicMock(returncode=1, stderr="Resolution error")
        return MagicMock(returncode=0, stdout="Success")

    mock_run.side_effect = run_side_effect

    profile = {
        "name": "Android",
        "dependencies": [
            "pydantic==2.13.4",
            "mcp>=1.28.1"
        ],
        "install_args": []
    }

    from shadow.core.dependencies import filter_unsupported_dependencies
    filtered = filter_unsupported_dependencies(profile, sys.executable, True)
    assert "mcp>=1.28.1" not in filtered["dependencies"]
    assert "pydantic==2.13.4" in filtered["dependencies"]

def test_detect_platform_all():
    # Verify we detect Linux, macOS, Windows, Android/Termux, Android Python
    with patch("sys.platform", "linux"), patch("os.path.exists", return_value=False), patch("os.environ", {}):
        assert detect_platform() == "Linux"

    with patch("sys.platform", "darwin"), patch("os.path.exists", return_value=False), patch("os.environ", {}):
        assert detect_platform() == "macOS"

    with patch("sys.platform", "win32"), patch("os.path.exists", return_value=False), patch("os.environ", {}):
        assert detect_platform() == "Windows"

    with patch("os.path.exists", lambda path: True if "com.termux" in path else False), patch("os.environ", {}):
        assert detect_platform() == "Android / Termux"

    with patch("os.path.exists", return_value=False), patch("os.environ", {"ANDROID_ROOT": "/system"}):
        assert detect_platform() == "Android Python"
