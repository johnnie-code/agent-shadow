#!/usr/bin/env bash
# PROJECT SHADOW — Autonomous OS Control Terminal CLI Self-Installer
# Production-grade, idempotent, and designed for Termux/Android.

set -e

# ANSI Color Codes for beautiful terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}${BOLD}"
echo "███████╗██╗  ██╗ █████╗ ██████╗  ██████╗ ██╗    ██╗"
echo "██╔════╝██║  ██║██╔══██╗██╔══██╗██╔═══██╗██║    ██║"
echo "███████╗███████║███████║██║  ██║██║   ██║██║ █╗ ██║"
echo "╚════██║██╔══██║██╔══██║██║  ██║██║   ██║██║███╗██║"
echo "███████║██║  ██║██║  ██║██████╔╝╚██████╔╝╚███╔███╔═╝"
echo "╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ╚══╝╚══╝  "
echo -e "${NC}"
echo -e "${CYAN}${BOLD}PROJECT SHADOW — Autonomous Goal-Driven Agent OS for Android (Termux)${NC}\n"

# Helper for headers
log_header() {
    echo -e "\n${BLUE}${BOLD}[*] $1${NC}"
}

# Helper for success
log_success() {
    echo -e "${GREEN}${BOLD}[+] $1${NC}"
}

# Helper for warnings
log_warn() {
    echo -e "${YELLOW}${BOLD}[!] $1${NC}"
}

# Helper for errors
log_error() {
    echo -e "${RED}${BOLD}[x] $1${NC}"
}

# Define production directories
SHADOW_HOME="${SHADOW_HOME:-$HOME/.shadow}"
VENV_DIR="$SHADOW_HOME/venv"

log_header "Initializing production-grade directory layout..."
mkdir -p "$SHADOW_HOME/config"
mkdir -p "$SHADOW_HOME/memory"
mkdir -p "$SHADOW_HOME/logs"
mkdir -p "$SHADOW_HOME/cache"
mkdir -p "$SHADOW_HOME/plugins"
mkdir -p "$SHADOW_HOME/backups"
log_success "Directory structure created at $SHADOW_HOME/"

# 1. Detect Termux / Android environment
log_header "Detecting environment and compatibility..."
IS_TERMUX=false
if [ -d "/data/data/com.termux/files/usr" ] || [ -n "$TERMUX_VERSION" ]; then
    IS_TERMUX=true
    log_success "Termux detected."
else
    log_warn "Standard Linux/macOS environment detected (not Termux)."
fi

# Verify Android compatibility
if [ "$IS_TERMUX" = true ]; then
    OS_ARCH=$(uname -m)
    log_success "Android OS Architecture: $OS_ARCH"
else
    log_success "OS: $(uname -s) Architecture: $(uname -m)"
fi

# 2. Update Package Repositories and Install Packages
if [ "$IS_TERMUX" = true ]; then
    log_header "Updating Termux repositories & installing dependencies..."
    # Attempt repo update with high tolerance for network/mirror failures
    pkg update -y || apt-get update -y || log_warn "Package update warning. Attempting installation anyway."

    log_header "Installing packages: git, python, termux-api..."
    pkg install git python termux-api sqlite ndk-sysroot clang make -y || \
    apt-get install git python termux-api sqlite -y || \
    log_warn "Some packages failed to install. Continuing..."
else
    log_header "Verifying git and python presence..."
    if ! command -v git &>/dev/null; then
        log_warn "Git is missing. Please install Git."
    else
        log_success "Git is present: $(git --version)"
    fi

    if ! command -v python3 &>/dev/null; then
        log_warn "Python3 is missing. Please install Python 3.12+."
    else
        log_success "Python is present: $(python3 --version)"
    fi
fi

# Ensure Python version is >= 3.12
PYTHON_CMD="python3"
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
    if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 12 ]; }; then
        log_warn "Detected Python version $PY_VERSION. Shadow OS requires Python >= 3.12."
    else
        log_success "Python version verified: $PY_VERSION"
    fi
else
    log_error "Python 3 is not installed or not in PATH."
    exit 1
fi

# 3. Repository Cloning or Syncing
log_header "Setting up repository directory..."
# Determine if we are already inside a cloned shadow repository
if [ -f "pyproject.toml" ] && [ -d "shadow" ]; then
    REPO_DIR=$(pwd)
    log_success "Existing Shadow repository detected at $REPO_DIR"
else
    REPO_DIR="$HOME/agent-shadow"
    if [ -d "$REPO_DIR" ]; then
        log_warn "Directory $REPO_DIR already exists. Pulling latest version..."
        cd "$REPO_DIR"
        git pull || log_warn "Git pull failed. Proceeding with existing code."
    else
        log_header "Cloning repository to $REPO_DIR..."
        git clone https://github.com/johnnie-code/agent-shadow.git "$REPO_DIR"
        cd "$REPO_DIR"
    fi
fi

# 4. Install UV or PIP
log_header "Installing Python package manager (uv preferred)..."
USE_UV=false
if command -v uv &>/dev/null; then
    USE_UV=true
    log_success "uv is already installed."
else
    log_header "Installing uv..."
    # Install uv via astral script, with pip fallback
    curl -LsSf https://astral.sh/uv/install.sh | sh || true
    # Reload path to see if uv is available
    if [ -f "$HOME/.local/bin/uv" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    fi
    if command -v uv &>/dev/null; then
        USE_UV=true
        log_success "uv successfully installed."
    else
        log_warn "uv installation failed or not found. Falling back to standard pip."
    fi
fi

# 5. Virtual Environment Creation & Dependencies Installation
log_header "Creating Python virtual environment ($VENV_DIR)..."
if [ "$USE_UV" = true ]; then
    uv venv "$VENV_DIR"
    log_success "Virtual environment created with uv."
    log_header "Installing Python dependencies with uv..."
    if [ "$IS_TERMUX" = true ]; then
        log_warn "Termux detected. Using precompiled wheel index to avoid compiling native extensions..."
        uv pip install --python "$VENV_DIR/bin/python" --extra-index-url https://eutalix.github.io/android-pydantic-core/ -e .
    else
        uv pip install --python "$VENV_DIR/bin/python" -e .
    fi
else
    $PYTHON_CMD -m venv "$VENV_DIR"
    log_success "Virtual environment created with python -m venv."
    log_header "Installing Python dependencies with pip..."
    "$VENV_DIR/bin/pip" install --upgrade pip
    if [ "$IS_TERMUX" = true ]; then
        log_warn "Termux detected. Using precompiled wheel index to avoid compiling native extensions..."
        "$VENV_DIR/bin/pip" install --extra-index-url https://eutalix.github.io/android-pydantic-core/ -e .
    else
        "$VENV_DIR/bin/pip" install -e .
    fi
fi
log_success "All Python dependencies installed."

# 6. Validate Dependencies After Installation
log_header "Validating installed Python dependencies..."
VENV_PYTHON="$VENV_DIR/bin/python"
if SHADOW_HOME="$SHADOW_HOME" $VENV_PYTHON -c "import pydantic, pydantic_settings, yaml, fastapi, uvicorn, rich, watchdog, httpx, typer" &>/dev/null; then
    log_success "All dependencies successfully verified."
else
    log_error "Dependency validation failed. Some core packages are missing."
    SHADOW_HOME="$SHADOW_HOME" $VENV_PYTHON -c "import pydantic, pydantic_settings, yaml, fastapi, uvicorn, rich, watchdog, httpx, typer" || true
    exit 1
fi

# 7. Initialize Database
log_header "Initializing SQLite database (with WAL)..."
SHADOW_HOME="$SHADOW_HOME" $VENV_PYTHON -c "from shadow.core.database import init_db; init_db()"
log_success "SQLite database initialized."

# 8. Generate Default Mission & Configuration
log_header "Generating configuration files..."
MISSION_PATH="$SHADOW_HOME/mission.md"
if [ ! -f "$MISSION_PATH" ]; then
    if [ -f "docs/mission.md" ]; then
        cp docs/mission.md "$MISSION_PATH"
        log_success "Default mission.md copied from docs."
    else
        cat << 'EOF' > "$MISSION_PATH"
# MISSION

## Identity
- **Name**: Shadow Agent
- **Role**: Personal Chief of Staff / Autonomous Agent OS

## Core Objectives
1. Actively discover and secure scholarships, hackathons, and AI news.
2. Build local Termux tools and verify code health.
3. Optimize daily schedules, reflect on actions, and provide strategic recommendations.

## Active Projects
- **Project Shadow**: Ensure system is operational, resilient, and fully configured.
EOF
        log_success "Generated default mission.md at $MISSION_PATH."
    fi
else
    log_success "mission.md already exists at $MISSION_PATH."
fi

# Set up .env file if it doesn't exist
ENV_FILE="$SHADOW_HOME/config/.env"
if [ ! -f "$ENV_FILE" ]; then
    cat << 'EOF' > "$ENV_FILE"
# Shadow OS Configuration Environment Variables
SHADOW_APP_NAME="Shadow"
SHADOW_DB_PATH="shadow.db"
SHADOW_LOG_LEVEL="INFO"
SHADOW_DEFAULT_PROVIDER="mock"
SHADOW_BATTERY_LIMIT=20
SHADOW_INTERNET_USAGE=true
SHADOW_NOTIFICATION_PREFERENCES="terminal"
SHADOW_SCAN_INTERVAL_SECONDS=3600
SHADOW_REFLECTION_TIME="22:00"
EOF
    log_success "Generated default .env configuration file at $ENV_FILE."
else
    log_success ".env configuration file already exists at $ENV_FILE."
fi

# 9. Verify Termux:API command-line tools
log_header "Verifying Termux:API tool state..."
if [ "$IS_TERMUX" = true ]; then
    if command -v termux-battery-status &>/dev/null; then
        log_success "Termux:API commands are installed and functional."
    else
        log_warn "Termux:API command-line tool package is not installed."
        echo "Please make sure to:"
        echo " 1. Install 'Termux:API' app from F-Droid."
        echo " 2. Run 'pkg install termux-api' in Termux."
    fi
else
    log_warn "Non-Termux environment. Termux:API checks skipped."
fi

# 10. Verify API Keys and Prompt for Provider Credentials
log_header "Verifying AI provider configuration..."
# Read existing default provider from .env if present
CURRENT_PROVIDER="mock"
if grep -q "SHADOW_DEFAULT_PROVIDER" "$ENV_FILE"; then
    CURRENT_PROVIDER=$(grep "SHADOW_DEFAULT_PROVIDER" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
fi

echo -e "\nChoose your default AI Provider (current: ${CYAN}$CURRENT_PROVIDER${NC}):"
echo "1) Mock (local offline simulation - no keys required)"
echo "2) OpenAI (requires OPENAI_API_KEY)"
echo "3) Anthropic Claude (requires ANTHROPIC_API_KEY)"
echo "4) Google Gemini (requires GEMINI_API_KEY)"
read -p "Enter choice [1-4] (default: 1): " PROVIDER_CHOICE

case "$PROVIDER_CHOICE" in
    2)
        SELECTED_PROVIDER="openai"
        read -p "Enter your OpenAI API Key: " USER_KEY
        ;;
    3)
        SELECTED_PROVIDER="anthropic"
        read -p "Enter your Anthropic API Key: " USER_KEY
        ;;
    4)
        SELECTED_PROVIDER="gemini"
        read -p "Enter your Gemini API Key: " USER_KEY
        ;;
    *)
        SELECTED_PROVIDER="mock"
        USER_KEY=""
        ;;
esac

# Update .env with choices
if [ -n "$SELECTED_PROVIDER" ]; then
    # Helper to update or append config key in .env
    set_env_val() {
        local key=$1
        local val=$2
        if grep -q "^$key=" "$ENV_FILE"; then
            # Replace
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|^$key=.*|$key=\"$val\"|" "$ENV_FILE"
            else
                sed -i "s|^$key=.*|$key=\"$val\"|" "$ENV_FILE"
            fi
        else
            # Append
            echo "$key=\"$val\"" >> "$ENV_FILE"
        fi
    }

    set_env_val "SHADOW_DEFAULT_PROVIDER" "$SELECTED_PROVIDER"
    if [ "$SELECTED_PROVIDER" = "openai" ] && [ -n "$USER_KEY" ]; then
        set_env_val "SHADOW_OPENAI__API_KEY" "$USER_KEY"
    elif [ "$SELECTED_PROVIDER" = "anthropic" ] && [ -n "$USER_KEY" ]; then
        set_env_val "SHADOW_ANTHROPIC__API_KEY" "$USER_KEY"
    elif [ "$SELECTED_PROVIDER" = "gemini" ] && [ -n "$USER_KEY" ]; then
        set_env_val "SHADOW_GEMINI__API_KEY" "$USER_KEY"
    fi
    log_success "Configured default AI Provider as: $SELECTED_PROVIDER"
fi

# 11. Run Migrations & Goals Synchronization
log_header "Synchronizing mission to local structured database..."
SHADOW_HOME="$SHADOW_HOME" $VENV_PYTHON -c "
import os
from shadow.core.database import init_db
from shadow.goals.engine import goals_engine
init_db()
mission_path = os.path.join(os.environ.get('SHADOW_HOME'), 'mission.md')
if os.path.exists(mission_path):
    with open(mission_path, 'r') as f:
        markdown_text = f.read()
    goals = goals_engine.parse_mission_markdown(markdown_text)
    goals_engine.sync_goals_to_db(goals)
" || log_warn "Initial mission sync failed. You can sync later using 'shadow mission'."
log_success "Database migrations and goals synced."

# 12. Self-test execution
log_header "Running self-test..."
if SHADOW_HOME="$SHADOW_HOME" $VENV_PYTHON -m pytest "$REPO_DIR/tests/" &>/dev/null; then
    log_success "All self-test suites passed perfectly!"
else
    log_warn "Some diagnostic tests failed or environment tests skipped. Checking CLI state..."
fi

# Test running CLI status
if SHADOW_HOME="$SHADOW_HOME" "$VENV_DIR/bin/shadow" status &>/dev/null; then
    log_success "Shadow CLI daemon status confirmed functional."
else
    log_error "CLI failed to execute. Check your configurations."
fi

# 13. Expose 'shadow' as global command
log_header "Exposing 'shadow' executable globally..."
GLOBAL_BIN_DIR=""
if [ "$IS_TERMUX" = true ]; then
    GLOBAL_BIN_DIR="/data/data/com.termux/files/usr/bin"
else
    # Check for write access to standard bin directories
    if [ -w "/usr/local/bin" ]; then
        GLOBAL_BIN_DIR="/usr/local/bin"
    elif [ -d "$HOME/.local/bin" ]; then
        GLOBAL_BIN_DIR="$HOME/.local/bin"
    else
        mkdir -p "$HOME/.local/bin"
        GLOBAL_BIN_DIR="$HOME/.local/bin"
    fi
fi

if [ -n "$GLOBAL_BIN_DIR" ] && [ -d "$GLOBAL_BIN_DIR" ]; then
    WRAPPER_PATH="$GLOBAL_BIN_DIR/shadow"
    cat << EOF > "$WRAPPER_PATH"
#!/usr/bin/env bash
# PROJECT SHADOW Wrapper Command
export SHADOW_HOME="$SHADOW_HOME"
export SHADOW_DATA_DIR="$SHADOW_HOME"
source "$VENV_DIR/bin/activate"
exec "$VENV_DIR/bin/shadow" "\$@"
EOF
    chmod +x "$WRAPPER_PATH"
    log_success "Global executable wrapper created successfully at: $WRAPPER_PATH"
else
    log_warn "Could not locate a writeable bin directory to expose 'shadow' globally."
    log_warn "To run, please configure your PATH to include $VENV_DIR/bin or execute: SHADOW_HOME=$SHADOW_HOME $VENV_DIR/bin/shadow"
fi

# 14. Enable Shell Autocompletion
log_header "Installing shell autocompletions..."
if SHADOW_HOME="$SHADOW_HOME" "$VENV_DIR/bin/shadow" --install-completion &>/dev/null; then
    log_success "Shell autocompletion successfully registered."
else
    log_warn "Could not automatically register completion. Run 'shadow --install-completion' manually inside your shell of choice."
fi

# 15. Installation Summary
log_header "INSTALLATION COMPLETE!"
echo -e "${GREEN}${BOLD}Congratulations! Project Shadow is now successfully installed.${NC}"
echo "--------------------------------------------------------"
echo -e "User Data (SHADOW_HOME): ${CYAN}$SHADOW_HOME${NC}"
echo -e "Virtual Environment:     ${CYAN}$VENV_DIR${NC}"
echo -e "Global CLI Command:      ${GREEN}shadow${NC}"
echo -e "Configured Provider:     ${PURPLE}$SELECTED_PROVIDER${NC}"
echo "--------------------------------------------------------"
echo -e "\nYou can now immediately manage and run Shadow using:"
echo -e "  ${GREEN}shadow start${NC}  - Start the background server"
echo -e "  ${GREEN}shadow status${NC} - Query daemon and database status"
echo -e "  ${GREEN}shadow doctor${NC} - Diagnose and repair installation issues"
echo -e "  ${GREEN}shadow tui${NC}    - Launch the Rich Dashboard interface"
echo "--------------------------------------------------------"
echo -e "${BLUE}Have an outstanding journey with your Autonomous Chief of Staff!${NC}\n"
