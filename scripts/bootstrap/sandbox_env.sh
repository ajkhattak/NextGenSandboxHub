#!/usr/bin/env bash

# Internal path initialization shared by the user-facing environment profile
# and bootstrap scripts. This file never modifies shell startup files.

if [ -n "${BASH_VERSION:-}" ]; then
    if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
        echo "ERROR: Source this script instead of executing it:"
        echo "  source ${BASH_SOURCE[0]}"
        exit 1
    fi
    ENV_SOURCE="${BASH_SOURCE[0]}"
elif [ -n "${ZSH_VERSION:-}" ]; then
    if [[ "${ZSH_EVAL_CONTEXT:-}" != *:file ]]; then
        echo "ERROR: Source this script instead of executing it:"
        echo "  source $0"
        exit 1
    fi
    ENV_SOURCE="${(%):-%N}"
else
    echo "ERROR: NextGenSandbox supports Bash and zsh environment profiles."
    return 1
fi

ENV_SCRIPT_DIR="$(cd "$(dirname "$ENV_SOURCE")" && pwd -P)"
PREVIOUS_SANDBOX_DIR="${SANDBOX_DIR:-}"
SANDBOX_DIR="$(cd "$ENV_SCRIPT_DIR/../.." && pwd -P)"

# Clear clone-relative defaults inherited from another checkout. Explicit
# build and data paths outside that checkout remain available to profiles.
if [ -n "$PREVIOUS_SANDBOX_DIR" ] && [ "$PREVIOUS_SANDBOX_DIR" != "$SANDBOX_DIR" ]; then
    for var in SANDBOX_BUILD_DIR SANDBOX_DATA_DIR SANDBOX_CONDARC; do
        eval "value=\${$var:-}"
        case "$value" in
            "$PREVIOUS_SANDBOX_DIR"/*) unset "$var" ;;
        esac
    done
fi

SANDBOX_BUILD_DIR="${SANDBOX_BUILD_DIR:-$SANDBOX_DIR/build}"
SANDBOX_DATA_DIR="${SANDBOX_DATA_DIR:-$SANDBOX_DIR/data}"
SANDBOX_CONDARC="${SANDBOX_CONDARC:-$SANDBOX_BUILD_DIR/condarc}"
NGEN_DIR="$SANDBOX_BUILD_DIR/ngen"
SANDBOX_ENV="$SANDBOX_BUILD_DIR/venv/sandbox"
FORCING_ENV="$SANDBOX_BUILD_DIR/venv/forcing"

export SANDBOX_DIR
export SANDBOX_BUILD_DIR
export SANDBOX_DATA_DIR
export SANDBOX_CONDARC
export NGEN_DIR
export SANDBOX_ENV
export FORCING_ENV
export CONDARC="$SANDBOX_CONDARC"
