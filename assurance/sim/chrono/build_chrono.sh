#!/usr/bin/env bash
# Build Project Chrono 9.0.1 (BSD 3-Clause) with Chrono::Vehicle and PyChrono from source, open-source parts only.
#
# The conda `pychrono` package of the projectchrono channel links Intel MKL and the NVIDIA CUDA libraries, which are
# free to use but not open source, so this track builds its own: core, vehicle, vehicle models and the Python module,
# no Irrlicht, CUDA, MKL, OpenCASCADE or co-simulation. The build tools (Python, numpy, SWIG, Eigen) come from the
# explicit conda-forge lock `chrono-build-linux-64.lock`, every package pinned by URL and md5.
#
#   build_chrono.sh <micromamba> <prefix>    # creates <prefix>/env (build tools) and <prefix>/chrono (install)
#
# Then run the pilot with:  <prefix>/env/bin/python chrono_pilot.py   and PYTHONPATH as printed at the end.
set -euo pipefail

MM="$1"
PREFIX="$(realpath -m "$2")"
HERE="$(cd "$(dirname "$0")" && pwd)"
TAG=9.0.1
COMMIT=2617649bf687456328a122b63dc0bb64df91394a

mkdir -p "$PREFIX"
MAMBA_ROOT_PREFIX="$PREFIX/mamba" "$MM" create -y -q -p "$PREFIX/env" --file "$HERE/chrono-build-linux-64.lock"
git clone -q --depth 1 --branch "$TAG" https://github.com/projectchrono/chrono.git "$PREFIX/src"
test "$(git -C "$PREFIX/src" rev-parse HEAD)" = "$COMMIT"
E="$PREFIX/env"
cmake -G Ninja -S "$PREFIX/src" -B "$PREFIX/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX/chrono" \
  -DUSE_SIMD=OFF -DBUILD_DEMOS=OFF -DBUILD_TESTING=OFF -DBUILD_BENCHMARKING=OFF \
  -DENABLE_MODULE_VEHICLE=ON -DENABLE_MODULE_VEHICLE_COSIM=OFF -DENABLE_MODULE_PYTHON=ON \
  -DEIGEN3_INCLUDE_DIR="$E/include/eigen3" -DSWIG_EXECUTABLE="$E/bin/swig" \
  -DPYTHON_EXECUTABLE="$E/bin/python3.13" -DPYTHON_LIBRARY="$E/lib/libpython3.13.so" \
  -DPYTHON_INCLUDE_DIR="$E/include/python3.13" > "$PREFIX/configure.log"
ninja -C "$PREFIX/build" install > "$PREFIX/build.log"
rm -rf "$PREFIX/src" "$PREFIX/build" "$PREFIX/mamba"
echo "PYTHONPATH=$(dirname "$(find "$PREFIX/chrono" -name __init__.py -path '*pychrono/__init__.py' | head -1)")/.."
