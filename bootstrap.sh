#!/usr/bin/env bash
#USAGE: ./bootstrap.sh --sandbox --subset --ngen --models --troute

set -e
#set -x

SETUP_ENV=OFF
BUILD_SANDBOX=OFF
BUILD_SUBSET=OFF
BUILD_NGEN=OFF
BUILD_MODELS=OFF
BUILD_TROUTE=OFF
CLEAN=false

# Parse args
for arg in "$@"; do
    case $arg in
      --env) SETUP_ENV=ON ;;
      --sandbox) BUILD_SANDBOX=ON ;;
      --subset)  BUILD_SUBSET=ON ;;
      --ngen)    BUILD_NGEN=ON ;;
      --models)  BUILD_MODELS=ON ;;
      --troute)  BUILD_TROUTE=ON ;;
      --clean)   CLEAN=true ;;
      *) echo "Unknown option: $arg"; exit 1 ;;
  esac
done

echo "========================================="
echo "Configuration:"
echo "  ENV      : $SETUP_ENV"
echo "  SANDBOX  : $BUILD_SANDBOX"
echo "  SUBSET   : $BUILD_SUBSET"
echo "  NGEN     : $BUILD_NGEN"
echo "  MODELS   : $BUILD_MODELS"
echo "  TROUTE   : $BUILD_TROUTE"
echo "========================================="


# Run steps
if [ "$SETUP_ENV" = "ON" ]; then
  source ./utils/sandbox_env.sh
fi

# Run steps
if [ "$BUILD_SANDBOX" = "ON" ]; then
  source ./utils/build_sandbox.sh
fi

if [ "$BUILD_SUBSET" = "ON" ]; then
  ./utils/build_venv_subset.sh
fi

if [ "$BUILD_NGEN" = "ON" ]; then
  source ./utils/build_models.sh NGEN=ON
fi

if [ "$BUILD_MODELS" = "ON" ]; then
  source ./utils/build_models.sh MODELS=ON CLEAN
fi

if [ "$BUILD_TROUTE" = "ON" ]; then
  source ./utils/build_models.sh TROUTE=ON
fi

echo "Done."

