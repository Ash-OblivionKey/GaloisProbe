cmake_minimum_required(VERSION 3.14)
project(openfhe_dump_keys LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

# OpenFHE: manual search via OPENFHE_ROOT (OpenFHE config does not export OpenFHE::openfhe)
if(NOT DEFINED OPENFHE_ROOT)
  message(STATUS "OpenFHE: skipped. Set OPENFHE_ROOT to build openfhe_dump_keys.")
  return()
endif()

find_path(OPENFHE_INCLUDE_DIR NAMES openfhe.h
  PATHS ${OPENFHE_ROOT}/include/openfhe/pke ${OPENFHE_ROOT}/include
  NO_DEFAULT_PATH)
find_path(OPENFHE_CORE_INCLUDE_DIR NAMES openfhecore.h
  PATHS ${OPENFHE_ROOT}/include/openfhe/core ${OPENFHE_ROOT}/include
  NO_DEFAULT_PATH)
find_library(OPENFHE_CORE_LIB NAMES OPENFHEcore
  PATHS ${OPENFHE_ROOT}/lib ${OPENFHE_ROOT}/lib64
  NO_DEFAULT_PATH)
find_library(OPENFHE_PKE_LIB NAMES OPENFHEpke
  PATHS ${OPENFHE_ROOT}/lib ${OPENFHE_ROOT}/lib64
  NO_DEFAULT_PATH)

if(NOT OPENFHE_INCLUDE_DIR OR NOT OPENFHE_CORE_INCLUDE_DIR OR NOT OPENFHE_CORE_LIB OR NOT OPENFHE_PKE_LIB)
  message(STATUS "OpenFHE not found at ${OPENFHE_ROOT}. Check include and lib paths.")
  return()
endif()

add_executable(openfhe_dump_keys dump_keys.cpp)
# OpenFHE install: pke/, core/, binfhe/, cereal/, third-party/ under include/openfhe
target_include_directories(openfhe_dump_keys PRIVATE
  ${OPENFHE_ROOT}/include/openfhe
  ${OPENFHE_ROOT}/include/openfhe/pke
  ${OPENFHE_ROOT}/include/openfhe/core
  ${OPENFHE_ROOT}/include/openfhe/binfhe
  ${OPENFHE_INCLUDE_DIR}
  ${OPENFHE_CORE_INCLUDE_DIR})
target_link_libraries(openfhe_dump_keys PRIVATE ${OPENFHE_PKE_LIB} ${OPENFHE_CORE_LIB})
