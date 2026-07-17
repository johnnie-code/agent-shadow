#!/bin/sh
# PROJECT SHADOW — Production Shell Installer for Termux/Linux
set -e

# ANSI Color Codes
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "${BLUE}============================================================${NC}"
echo "${GREEN}        PROJECT SHADOW — AUTOMATED SYSTEM INSTALLER${NC}"
echo "${BLUE}============================================================${NC}"

# Detect Termux Environment
IS_TERMUX=0
if [ -d "/data/data/com.termux" ] || [ -n "$TERMUX_VERSION" ]; then
    IS_TERMUX=1
    echo "[*] Detected Termux (Android) environment."
fi

# Automatic package installation for Termux
if [ "$IS_TERMUX" -eq 1 ]; then
    echo "[*] Updating package index and installing system packages (python, git, sqlite)..."
    # Suppress prompts, run non-interactively
    pkg update -y || true
    pkg install -y python git sqlite || true
fi

# Check for Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "${RED}Error: Python 3 is required but was not found on your system.${NC}"
    if [ "$IS_TERMUX" -eq 1 ]; then
        echo "Please run: pkg install python"
    else
        echo "Please install python3 using your system's package manager (apt, dnf, pacman, brew, etc.)"
    fi
    exit 1
fi

echo "[*] Launching native installation engine..."
python3 install.py
