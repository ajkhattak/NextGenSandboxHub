#!/usr/bin/env bash

# Prevent multiple initializations
if [ -n "$SANDBOX_ENV_LOADED" ]; then
    return 0 2>/dev/null || exit 0
fi
export SANDBOX_ENV_LOADED=1


if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Please source this script instead of running it:"
    echo "source $(basename "$0")"
    exit 1
fi

######## PATH DETECTION #########

if [ -n "${BASH_SOURCE[0]:-}" ]; then
    SOURCE="${BASH_SOURCE[0]}"
else
    SOURCE="$0"
fi


SCRIPT_DIR="$(cd "$(dirname "$SOURCE")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/$(basename "$SOURCE")"

SANDBOX_DIR="$(dirname "$SCRIPT_DIR")"

SANDBOX_BUILD_DIR="$(dirname "$SANDBOX_DIR")/sandbox_build"

NGEN_DIR="$SANDBOX_BUILD_DIR/ngen"

VENV_SANDBOX_PATH="$SANDBOX_BUILD_DIR/venv/venv_sandbox_py3.11"
VENV_FORCING_PATH="$SANDBOX_BUILD_DIR/venv/venv_forcing"


export SANDBOX_DIR
export SANDBOX_BUILD_DIR
export NGEN_DIR
export VENV_SANDBOX_PATH
export VENV_FORCING_PATH


if ! grep -Fxq "source $SCRIPT_PATH" "$HOME/.zshrc" 2>/dev/null && \
   ! grep -Fxq "source $SCRIPT_PATH" "$HOME/.bashrc" 2>/dev/null; then

    ######## INFO OUTPUT #########

    echo ""
    echo "Sandbox environment initialized:"
    echo "SANDBOX_DIR        : $SANDBOX_DIR"
    echo "SANDBOX_BUILD_DIR  : $SANDBOX_BUILD_DIR"
    echo "NGEN_DIR           : $NGEN_DIR"
    echo "VENV_SANDBOX_PATH  : $VENV_SANDBOX_PATH"
    echo "VENV_FORCING_PATH  : $VENV_FORCING_PATH"
    echo ""

    echo ""
    echo "ACTION REQUIRED:"
    echo "You MUST add the following line to your shell configuration file to continue:"
    echo ""
    echo "  source $SCRIPT_PATH"
    echo ""

    if [[ "$SHELL" == *zsh ]]; then
	TARGET_FILE="$HOME/.zshrc"
    elif [[ "$SHELL" == *bash ]]; then
	if [ -f "$HOME/.bash_profile" ]; then
            TARGET_FILE="$HOME/.bash_profile"
	else
            TARGET_FILE="$HOME/.bashrc"
	fi
    else
	echo "Unsupported shell: $SHELL_NAME"
	return 1
    fi


    echo "Run this command:"
    echo ""
    echo "  echo \"source $SCRIPT_PATH\" >> $TARGET_FILE"
    echo ""
    echo "Then reload your shell:"
    echo ""
    echo "  source $TARGET_FILE"
    echo ""

fi





