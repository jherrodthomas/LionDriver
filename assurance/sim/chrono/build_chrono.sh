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
# It prints the command that runs the pilot on the build. About 80 min of CPU on 4 cores.
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
# Without the Irrlicht module SWIG takes ChVehicleVisualSystem for a concrete class and wraps a constructor the C++
# compiler then refuses (the class is abstract); the pilot never constructs one, so the constructor is not wrapped
I="$PREFIX/src/src/chrono_swig/interface/vehicle/ChModuleVehicle.i"
sed -i 's|^%shared_ptr(chrono::vehicle::ChVehicleVisualSystem)$|&\n%ignore chrono::vehicle::ChVehicleVisualSystem::ChVehicleVisualSystem;|' "$I"
grep -q '^%ignore chrono::vehicle::ChVehicleVisualSystem::ChVehicleVisualSystem;$' "$I"
E="$PREFIX/env"
cmake -G Ninja -S "$PREFIX/src" -B "$PREFIX/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX/chrono" \
  -DUSE_SIMD=OFF -DBUILD_DEMOS=OFF -DBUILD_TESTING=OFF -DBUILD_BENCHMARKING=OFF \
  -DENABLE_MODULE_VEHICLE=ON -DENABLE_MODULE_VEHICLE_COSIM=OFF -DENABLE_MODULE_PYTHON=ON \
  -DEIGEN3_INCLUDE_DIR="$E/include/eigen3" -DSWIG_EXECUTABLE="$E/bin/swig" \
  -DPYTHON_EXECUTABLE="$E/bin/python3.13" -DPYTHON_LIBRARY="$E/lib/libpython3.13.so" \
  -DPYTHON_INCLUDE_DIR="$E/include/python3.13" > "$PREFIX/configure.log"
ninja -C "$PREFIX/build" install > "$PREFIX/build.log"
# the install puts the extension modules beside the pychrono package; its modules import them from inside it
PY="$PREFIX/chrono/share/chrono/python"
mv "$PY"/_*.so "$PY/pychrono/"
rm -rf "$PREFIX/src" "$PREFIX/build" "$PREFIX/mamba"
echo "run with: LD_LIBRARY_PATH=$PREFIX/chrono/lib PYTHONPATH=$PY $PREFIX/env/bin/python chrono_pilot.py"
