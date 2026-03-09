cmake_minimum_required(VERSION 3.14)
project(KeySwitchingInstrumentation LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

# SEAL instrumentation (optional: cmake -DSEAL_ROOT=/path/to/SEAL-install)
if(DEFINED SEAL_ROOT)
  add_subdirectory(seal)
else()
  message(STATUS "SEAL: skipped. Set SEAL_ROOT to build seal_dump_keys.")
endif()

# HElib instrumentation (optional: cmake -DUSE_HELIB=ON -DHELIB_ROOT=...)
add_subdirectory(helib)

# OpenFHE instrumentation (optional: cmake -DOPENFHE_ROOT=/path/to/OpenFHE)
add_subdirectory(openfhe)
