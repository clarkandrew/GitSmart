#!/bin/bash

# GitSmart Setup Script
# This script automates the installation process for GitSmart

set -e  # Exit on error

# Define color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===== GitSmart Installation Script =====${NC}"
echo

# Get absolute path of the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check Python version
if command -v python3 &>/dev/null; then
    python_cmd="python3"
elif command -v python &>/dev/null; then
    python_cmd="python"
else
    echo -e "${RED}Error: Python not found. Please install Python 3.7 or higher.${NC}"
    exit 1
fi

# Verify Python version is 3.7+
python_version=$($python_cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
required_version="3.7"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo -e "${RED}Error: Python version $python_version detected. GitSmart requires Python 3.7 or higher.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python $python_version detected${NC}"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $python_cmd -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Determine the correct activation command
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo -e "${RED}Error: Could not find virtual environment activation script.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Get the absolute path to the Python executable in the virtual environment
if [ -f "venv/bin/python" ]; then
    VENV_PYTHON_PATH="$(cd "$(dirname "venv/bin/python")" && pwd)/$(basename "venv/bin/python")"
elif [ -f "venv/Scripts/python.exe" ]; then
    VENV_PYTHON_PATH="$(cd "$(dirname "venv/Scripts/python.exe")" && pwd)/$(basename "venv/Scripts/python.exe")"
else
    echo -e "${RED}Error: Could not find Python executable in the virtual environment.${NC}"
    exit 1
fi

# Function to check internet connection
check_internet() {
    # Try to connect to Google's DNS server
    if ping -c 1 -W 1 8.8.8.8 &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Install dependencies with error handling
echo "Installing dependencies..."
if check_internet; then
    pip install -q --disable-pip-version-check pip setuptools wheel
    if pip install -r requirements.txt -q; then
        echo -e "${GREEN}✓ Dependencies installed${NC}"
        dependencies_installed=true
    else
        echo -e "${YELLOW}Warning: Failed to install some dependencies.${NC}"
        dependencies_installed=false
    fi
else
    echo -e "${YELLOW}Warning: No internet connection detected. Skipping dependency installation.${NC}"
    dependencies_installed=false
fi

# Install package in development mode with error handling
echo "Installing GitSmart package..."
if [ "$dependencies_installed" = true ] && check_internet; then
    if pip install -e . -q; then
        echo -e "${GREEN}✓ GitSmart package installed${NC}"
        package_installed=true
    else
        echo -e "${YELLOW}Warning: Failed to install GitSmart package. Aliases will still be set up.${NC}"
        package_installed=false
    fi
else
    echo -e "${YELLOW}Warning: Skipping GitSmart package installation. Aliases will still be set up.${NC}"
    package_installed=false
fi

# Configure application
if [ ! -f "config.ini" ] && [ -f "example.config.ini" ]; then
    echo "Creating config.ini from example..."
    cp example.config.ini config.ini
    echo -e "${GREEN}✓ Configuration file created (please update with your API credentials)${NC}"
elif [ -f "config.ini" ]; then
    echo -e "${GREEN}✓ Configuration file already exists${NC}"
else
    echo -e "${YELLOW}Warning: example.config.ini not found. You'll need to create a config.ini file manually.${NC}"
fi

# Set up aliases
shell_config=""
if [ -n "$BASH_VERSION" ] && [ -f "$HOME/.bashrc" ]; then
    shell_config="$HOME/.bashrc"
elif [ -n "$ZSH_VERSION" ] && [ -f "$HOME/.zshrc" ]; then
    shell_config="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    shell_config="$HOME/.bashrc"
elif [ -f "$HOME/.zshrc" ]; then
    shell_config="$HOME/.zshrc"
fi

# Create alias command string
GITSMART_CMD="$VENV_PYTHON_PATH -m GitSmart.main"

# Create temporary alias file that will be sourced at the end
TMP_ALIAS_FILE="$PROJECT_DIR/.gitsmart_aliases"
echo "#!/bin/bash" > "$TMP_ALIAS_FILE"
echo "alias gitsmart='$GITSMART_CMD'" >> "$TMP_ALIAS_FILE"
echo "alias c='gitsmart'" >> "$TMP_ALIAS_FILE"
chmod +x "$TMP_ALIAS_FILE"

if [ -n "$shell_config" ]; then
    echo "Setting up aliases in $shell_config..."
    
    # Remove any existing GitSmart aliases to avoid duplicates
    if grep -q "# GitSmart aliases" "$shell_config"; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS requires an empty string after -i
            sed -i '' '/# GitSmart aliases/,/alias c=/d' "$shell_config" 2>/dev/null || true
        else
            # Linux/other Unix variants
            sed -i '/# GitSmart aliases/,/alias c=/d' "$shell_config" 2>/dev/null || true
        fi
    fi
    
    # Add new aliases to shell config
    echo -e "\n# GitSmart aliases" >> "$shell_config"
    echo "alias gitsmart='$GITSMART_CMD'" >> "$shell_config"
    echo "alias c='gitsmart'" >> "$shell_config"
    
    echo -e "${GREEN}✓ Aliases added to $shell_config${NC}"
else
    echo -e "${YELLOW}No shell configuration file found for permanent aliases.${NC}"
    echo -e "\n${YELLOW}To permanently add aliases, add these lines to your shell configuration file:${NC}"
    echo -e "   alias gitsmart='$GITSMART_CMD'"
    echo -e "   alias c='gitsmart'"
fi

echo
echo -e "${BLUE}===== GitSmart Setup Complete! =====${NC}"
echo -e "To use GitSmart, navigate to any Git repository and run:"
echo -e "   ${GREEN}gitsmart${NC}  # or the shorter alias: ${GREEN}c${NC}"

if [ "$package_installed" = false ]; then
    echo -e "${YELLOW}Note: Some installation steps were skipped due to connectivity issues.${NC}"
    echo -e "${YELLOW}You may want to run this script again later with a better internet connection.${NC}"
fi

echo -e "${YELLOW}Remember to update your config.ini with your API credentials.${NC}"
echo

echo -e "${BLUE}===== Activating Aliases in Current Session =====${NC}"
echo -e "To use the aliases in your current terminal session, run:"
echo -e "${GREEN}source $TMP_ALIAS_FILE${NC}"
echo