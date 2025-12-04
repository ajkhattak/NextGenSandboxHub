#!/usr/bin/env bash
set -euo pipefail

### --------- Config -----------------
# Set PYTHON_INSTALL_DIR to a local dir
PYTHON_INSTALL_DIR="<path_to_install_dir>" # Example:  /scratch/username/software/python311


PYTHON_VERSION="3.11.12"
BUILD_DIR="${PYTHON_INSTALL_DIR}_build"
TARBALL="Python-${PYTHON_VERSION}.tgz"
SOURCE_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/${TARBALL}"


### Create Directories
echo "Creating install and build directories..."
mkdir -p "${PYTHON_INSTALL_DIR}"
mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"


### Download Tarball
if [ ! -f "${TARBALL}" ]; then
    echo "Downloading Python ${PYTHON_VERSION}..."
    wget "${SOURCE_URL}"
fi

echo "Extracting Python source..."
tar -xf "${TARBALL}"
cd "Python-${PYTHON_VERSION}"


### -------- Set Compilers ------------------
export CC=$(which gcc)
export CXX=$(which g++)

### ----------- Configure Build --------------
echo "Configuring build..."
./configure \
    --prefix="${PYTHON_INSTALL_DIR}" \
    --enable-optimizations=no \
    --with-lto=no


### ----------- Build & Install---------------
echo "Building Python..."
make -j "$(nproc)"

echo "Installing Python to ${PYTHON_INSTALL_DIR}..."
make install


### -------------- Summary --------------------
echo
echo "------------------------------------"
echo "Python ${PYTHON_VERSION} installed at:"
echo "  ${PYTHON_INSTALL_DIR}"
echo
echo "Binaries:"
ls -l "${PYTHON_INSTALL_DIR}/bin"
echo
echo "To use this Python, run:"
echo "  export PATH=${PYTHON_INSTALL_DIR}/bin:\$PATH"
echo
echo "python3.11 path check:"
echo "  ${PYTHON_INSTALL_DIR}/bin/python3.11 --version"
echo "------------------------------------"
