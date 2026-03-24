#!/usr/bin/env bash
#USAGE: ./bootstrap.sh --sandbox --subset --ngen --models --troute

set -e

BUILD_SANDBOX=OFF
BUILD_SUBSET_ENV=OFF
BUILD_NGEN=OFF
BUILD_MODELS=OFF
BUILD_TROUTE=OFF

# Parse args
for arg in "$@"; do
  case $arg in
    --sandbox) BUILD_SANDBOX=ON ;;
    --subset) BUILD_SUBSET=ON ;;
    --ngen) BUILD_NGEN=ON ;;
    --models) BUILD_MODELS=ON ;;
    --troute) BUILD_TROUTE=ON ;;
    *) echo "Unknown option: $arg"; exit 1 ;;
  esac
done

echo "Configuration:"
echo "  SANDBOX: $BUILD_SANDBOX"
echo "  SUBSET ENV: $BUILD_SUBSET_ENV"
echo "  MODELS: $BUILD_MODELS"

# Run steps
if [ "$BUILD_SANDBOX" = "ON" ]; then
  echo "Building sandbox..."
  source ./utils/build_sandbox.sh
fi

if [ "$BUILD_SUBSET" = "ON" ]; then
  echo "Building subset environment..."
  ./utils/build_venv_subset.sh
fi

if [ "$BUILD_NGEN" = "ON" ]; then
  source ./utils/build_models.sh NGEN=ON
fi

if [ "$BUILD_MODELS" = "ON" ]; then
  source ./utils/build_models.sh MODELS=ON
fi

if [ "$BUILD_TROUTE" = "ON" ]; then
  source ./utils/build_models.sh TROUTE=ON
fi

echo "Done."

