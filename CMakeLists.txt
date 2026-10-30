cmake_minimum_required(VERSION 3.22 FATAL_ERROR)

project(lira-simgen-lib
  VERSION 0.1.0
  DESCRIPTION "LIRA-driven simulator generator framework"
  LANGUAGES NONE)

include(cmake/CPM.cmake)

CPMAddPackage(
  NAME LIRA
  GITHUB_REPOSITORY ProteusLab/LIRA
  GIT_TAG v0.1.1
)


set(ARCH_TARGET "" CACHE STRING "Target architecture")

if(ARCH_TARGET STREQUAL "")
  message(FATAL_ERROR "ARCH_TARGET is required (e.g. -DARCH_TARGET=RISC_V)")
endif()

# Shared build output layout.
set(INTERP_OUT_DIR "${CMAKE_BINARY_DIR}/interpreter"
    CACHE PATH "Directory for the generated interpreter sources and binary")

set(LIRA_IR_DIR "${CMAKE_BINARY_DIR}/lira_ir"
    CACHE PATH "Directory for the generated LIRA IR")

set(ARCH_SOURCE "" CACHE STRING
    "Architecture description source (Protea, ASL)")

find_package(Python3 COMPONENTS Interpreter REQUIRED)

get_filename_component(LIRA_PYTHON_ROOT "${LIRA_PYTHON_DIR}" DIRECTORY)

set(GENERATOR_ENV
  ${CMAKE_COMMAND} -E env "PYTHONPATH=${CMAKE_SOURCE_DIR}:${LIRA_PYTHON_ROOT}")

if(ARCH_SOURCE STREQUAL "")
  message(FATAL_ERROR "ARCH_SOURCE is required (e.g. -DARCH_SOURCE=Protea)")
elseif(ARCH_SOURCE STREQUAL "Protea")
  include(cmake/fetch_protea.cmake)
  add_subdirectory(utils/protea2lira)
elseif(ARCH_SOURCE STREQUAL "ASL")
  message(FATAL_ERROR "ARCH_SOURCE=ASL is not implemented yet")
else()
  message(FATAL_ERROR
    "unknown ARCH_SOURCE '${ARCH_SOURCE}' (expected Protea or ASL)")
endif()

enable_language(CXX)

# Common generator inputs: any Python/Jinja change re-triggers generation.
file(GLOB_RECURSE GENERATOR_DEPS CONFIGURE_DEPENDS
  "${CMAKE_SOURCE_DIR}/lib/*.py"
  "${CMAKE_SOURCE_DIR}/lib/*.jinja"
  "${CMAKE_SOURCE_DIR}/cpp/*.py"
  "${CMAKE_SOURCE_DIR}/cpp/*.jinja"
  "${CMAKE_SOURCE_DIR}/decoder/*.py"
  "${CMAKE_SOURCE_DIR}/decoder/*.jinja"
  "${CMAKE_SOURCE_DIR}/encoder/*.py"
  "${CMAKE_SOURCE_DIR}/encoder/*.jinja"
)

include(cmake/LiraGenerator.cmake)

add_subdirectory(cpp)
add_subdirectory(decoder)
add_subdirectory(encoder)
