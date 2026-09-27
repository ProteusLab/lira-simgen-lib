enable_language(CXX)

CPMAddPackage(
  NAME elfio
  GITHUB_REPOSITORY serge1/ELFIO
  GIT_TAG Release_3.12
  EXCLUDE_FROM_ALL True
)

CPMAddPackage(
  NAME CLI11
  GITHUB_REPOSITORY CLIUtils/CLI11
  VERSION 2.5.0
  EXCLUDE_FROM_ALL True
)

CPMAddPackage(
  NAME fmt
  GITHUB_REPOSITORY fmtlib/fmt
  GIT_TAG 12.0.0
  EXCLUDE_FROM_ALL True
)

find_package(Python3 COMPONENTS Interpreter REQUIRED)

set(INTERP_OUT_DIR "${CMAKE_BINARY_DIR}/interpreter"
    CACHE PATH "Directory for the generated interpreter sources")

set(INTERPRETER_SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}")
set(INTERP_RUNTIME_DIR "${INTERPRETER_SOURCE_DIR}/runtime")
set(INTERP_TARGET_DIR "${INTERPRETER_SOURCE_DIR}/Target/${ARCH_TARGET}")

# Target description: sets TARGET_IR, TARGET_RUNTIME_SOURCES and TARGET_SIM_MAIN
include(${INTERP_TARGET_DIR}/target.cmake)

set(INTERP_GENERATED
  ${INTERP_OUT_DIR}/isa.hh
  ${INTERP_OUT_DIR}/snippets.hh
  ${INTERP_OUT_DIR}/snippets.cc
  ${INTERP_OUT_DIR}/decoder.hh
  ${INTERP_OUT_DIR}/decoder.cc
  ${INTERP_OUT_DIR}/base_ops.hh
  ${INTERP_OUT_DIR}/base_ops.cc
  ${INTERP_OUT_DIR}/cpu_state.hh
  ${INTERP_OUT_DIR}/cpu_state.cc
  ${INTERP_OUT_DIR}/naive_interpreter.hh
  ${INTERP_OUT_DIR}/naive_interpreter.cc
)

file(GLOB INTERP_GENERATOR_DEPS
  ${INTERPRETER_SOURCE_DIR}/*.py
  ${INTERPRETER_SOURCE_DIR}/templates/*.jinja
  ${INTERPRETER_SOURCE_DIR}/Target/*.py
  ${INTERP_TARGET_DIR}/*.py
  ${INTERP_TARGET_DIR}/templates/*.jinja
  ${CMAKE_SOURCE_DIR}/lib/*.py
  ${CMAKE_SOURCE_DIR}/lib/cpp/*.py
  ${CMAKE_SOURCE_DIR}/lib/cpp/templates/*.jinja
)
list(APPEND INTERP_GENERATOR_DEPS ${TARGET_IR})

add_custom_command(
  OUTPUT ${INTERP_GENERATED}
  DEPENDS ${INTERP_GENERATOR_DEPS}
  COMMAND ${CMAKE_COMMAND} -E make_directory ${INTERP_OUT_DIR}
  COMMAND ${CMAKE_COMMAND} -E env
          "PYTHONPATH=${CMAKE_SOURCE_DIR}"
          ${Python3_EXECUTABLE}
          ${INTERPRETER_SOURCE_DIR}/main.py
          --ir-path ${TARGET_IR}
          --out-dir ${INTERP_OUT_DIR}
          --target ${ARCH_TARGET}
  COMMENT "Generating LIRA interpreter sources"
)

add_custom_target(gen-interp DEPENDS ${INTERP_GENERATED})

# Generated interpreter + generic and target runtime (everything but main)
add_library(interp-core OBJECT
  ${INTERP_OUT_DIR}/decoder.cc
  ${INTERP_OUT_DIR}/snippets.cc
  ${INTERP_OUT_DIR}/base_ops.cc
  ${INTERP_OUT_DIR}/naive_interpreter.cc
  ${INTERP_OUT_DIR}/cpu_state.cc
  ${INTERP_RUNTIME_DIR}/base_exec_engine.cc
  ${INTERP_RUNTIME_DIR}/hart.cc
  ${INTERP_RUNTIME_DIR}/memory.cc
  ${INTERP_RUNTIME_DIR}/elf_loader.cc
  ${TARGET_RUNTIME_SOURCES}
)
set_target_properties(interp-core PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_include_directories(interp-core PUBLIC
  ${INTERP_OUT_DIR}
  ${INTERP_RUNTIME_DIR}
  ${INTERP_RUNTIME_DIR}/Target/${ARCH_TARGET}
)
target_link_libraries(interp-core PUBLIC elfio CLI11 fmt)
target_compile_features(interp-core PUBLIC cxx_std_20)

add_executable(sim-interp ${TARGET_SIM_MAIN})
set_target_properties(sim-interp PROPERTIES
  OUTPUT_NAME interpreter
  RUNTIME_OUTPUT_DIRECTORY "${INTERP_OUT_DIR}")
target_link_libraries(sim-interp PRIVATE interp-core)

add_custom_target(build-interp DEPENDS sim-interp)

# Optional target-specific extras (e.g. test libraries)
if(EXISTS ${INTERP_TARGET_DIR}/extra.cmake)
  include(${INTERP_TARGET_DIR}/extra.cmake)
endif()
