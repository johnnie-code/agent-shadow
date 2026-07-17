#!/usr/bin/env bash
# PROJECT SHADOW — Autonomous OS Control Terminal CLI Bootstrap Installer for Termux
# This script prepares a clean Termux environment, installs dependencies, and sets up Shadow OS.

set -e

# ANSI escape codes for formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}        PROJECT SHADOW — Termux Production Installer             ${NC}"
echo -e "${BLUE}================================================================${NC}"

# 1. Detect environment and verify we are in Termux or a supported Linux environment
if [ -d "/data/data/com.termux/files/usr" ]; then
    echo -e "${GREEN}[✔] Termux environment detected.${NC}"
    IS_TERMUX=true
else
    echo -e "${YELLOW}[!] Warning: Not in a Termux environment. Proceeding with standard installation...${NC}"
    IS_TERMUX=false
fi

# 2. Update Termux packages if in Termux
if [ "$IS_TERMUX" = true ]; then
    echo -e "${CYAN}[1/6] Updating Termux packages...${NC}"
    # Suppress prompts to ensure a non-interactive/smooth script run
    pkg update -y -o Dpkg::Options::="--force-confold"
    pkg upgrade -y -o Dpkg::Options::="--force-confold"

    echo -e "${CYAN}[2/6] Installing required system packages (python, git)...${NC}"
    pkg install -y python git
else
    echo -e "${CYAN}[1/6] Skipping Termux package updates (non-Termux system).${NC}"
fi

# 3. Create a Python Virtual Environment
echo -e "${CYAN}[3/6] Setting up Python virtual environment...${NC}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}[!] Virtual environment 'venv' already exists. Reusing it...${NC}"
else
    python3 -m venv venv
    echo -e "${GREEN}[✔] Virtual environment 'venv' created successfully.${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip, setuptools, and wheel
echo -e "${CYAN}[4/6] Upgrading package managers inside virtual environment...${NC}"
pip install --upgrade pip setuptools wheel

# 4. Install dependencies (with Termux precompiled wheels workaround if in Termux)
echo -e "${CYAN}[5/6] Installing dependencies...${NC}"
if [ "$IS_TERMUX" = true ]; then
    echo -e "${YELLOW}[!] Termux detected. Installing 'pydantic-core' using precompiled wheels index...${NC}"
    # Installing pydantic-core with the extra index url first avoids compiling it from Rust source.
    pip install pydantic-core --extra-index-url https://eutalix.github.io/android-pydantic-core/
fi

# Install the package in editable mode with development/testing requirements
echo -e "${CYAN}Installing PROJECT SHADOW package in editable mode...${NC}"
if [ "$IS_TERMUX" = true ]; then
    pip install -e . --extra-index-url https://eutalix.github.io/android-pydantic-core/
    pip install pytest pytest-asyncio
else
    pip install -e .
    pip install pytest pytest-asyncio
fi

# 5. Initialize the SQLite database
echo -e "${CYAN}[6/6] Initializing local database and syncing goals...${NC}"
# Use the CLI to initialize the database
if [ -f "mission.md" ]; then
    python3 -m shadow.cli.main update
else
    # Create a dummy mission.md if not present
    echo -e "# Mission\n\n- Goal 1: Initialize Project Shadow\n  - Category: Core\n  - Priority: High\n  - Status: Active" > mission.md
    python3 -m shadow.cli.main update
fi

echo -e "${GREEN}[✔] Database initialized and mission synced.${NC}"

# 6. Verify installation
echo -e "${CYAN}Verifying installation...${NC}"
if python3 -m shadow.cli.main --help > /dev/null 2>&1; then
    echo -e "${GREEN}[✔] CLI verification successful!${NC}"
else
    echo -e "${RED}[✘] CLI verification failed. Please check logs.${NC}"
    exit 1
fi

echo -e "${BLUE}================================================================${NC}"
echo -e "${GREEN}      PROJECT SHADOW has been successfully installed!            ${NC}"
echo -e "${BLUE}================================================================${NC}"
echo -e "To start using Shadow OS:"
echo -e "  1. Activate the virtual environment:  ${CYAN}source venv/bin/activate${NC}"
echo -e "  2. Show help:                         ${CYAN}shadow --help${NC}"
echo -e "  3. Start the background API daemon:  ${CYAN}shadow start --background${NC}"
echo -e "  4. Launch the dashboard TUI:          ${CYAN}python3 -m shadow.cli.tui${NC}"
echo -e "================================================================"
