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

set(INTERP_GENERATOR_DEPS
  ${INTERPRETER_SOURCE_DIR}/main.py
  ${INTERPRETER_SOURCE_DIR}/config.py
  ${INTERPRETER_SOURCE_DIR}/emitter.py
  ${INTERPRETER_SOURCE_DIR}/interface.py
  ${INTERPRETER_SOURCE_DIR}/templates.py
  ${INTERPRETER_SOURCE_DIR}/templates/isa.hh.jinja
  ${INTERPRETER_SOURCE_DIR}/templates/decoder.hh.jinja
  ${INTERPRETER_SOURCE_DIR}/templates/decoder.cc.jinja
  ${INTERPRETER_SOURCE_DIR}/templates/naive_interpreter.hh.jinja
  ${INTERPRETER_SOURCE_DIR}/templates/naive_interpreter.cc.jinja
  ${INTERPRETER_SOURCE_DIR}/templates/snippets.hh.jinja
  ${INTERPRETER_SOURCE_DIR}/templates/snippets.cc.jinja
  ${INTERPRETER_SOURCE_DIR}/templates/base_ops.hh.jinja
  ${INTERPRETER_SOURCE_DIR}/templates/base_ops.cc.jinja
  ${INTERPRETER_SOURCE_DIR}/templates/cpu_state.hh.jinja
  ${INTERPRETER_SOURCE_DIR}/templates/cpu_state.cc.jinja
  ${INTERPRETER_SOURCE_DIR}/Target/__init__.py
  ${INTERPRETER_SOURCE_DIR}/Target/RISC_V/__init__.py
  ${INTERPRETER_SOURCE_DIR}/Target/RISC_V/regfile.py
  ${INTERPRETER_SOURCE_DIR}/Target/RISC_V/interface.py
  ${INTERPRETER_SOURCE_DIR}/Target/RISC_V/base_ops.py
  ${INTERPRETER_SOURCE_DIR}/Target/RISC_V/templates.py
  ${CMAKE_SOURCE_DIR}/lib/builders.py
  ${CMAKE_SOURCE_DIR}/lib/driver.py
  ${CMAKE_SOURCE_DIR}/lib/instruction.py
  ${CMAKE_SOURCE_DIR}/lib/interface.py
  ${CMAKE_SOURCE_DIR}/lib/nodes.py
  ${CMAKE_SOURCE_DIR}/lib/operand.py
  ${CMAKE_SOURCE_DIR}/lib/regfile.py
  ${CMAKE_SOURCE_DIR}/lib/types.py
  ${CMAKE_SOURCE_DIR}/lib/cpp/nodes.py
  ${CMAKE_SOURCE_DIR}/lib/cpp/base_ops.py
  ${CMAKE_SOURCE_DIR}/lib/cpp/func.py
  ${CMAKE_SOURCE_DIR}/lib/cpp/templates.py
  ${CMAKE_SOURCE_DIR}/data/${ARCH_TARGET}/RV32I.yaml
)

file(GLOB LIB_CPP_TEMPLATES "${CMAKE_SOURCE_DIR}/lib/cpp/templates/*.jinja")
list(APPEND INTERP_GENERATOR_DEPS ${LIB_CPP_TEMPLATES})

file(GLOB INTERP_TARGET_TEMPLATES
     "${INTERPRETER_SOURCE_DIR}/Target/RISC_V/templates/*.jinja")
list(APPEND INTERP_GENERATOR_DEPS ${INTERP_TARGET_TEMPLATES})

add_custom_command(
  OUTPUT ${INTERP_GENERATED}
  DEPENDS ${INTERP_GENERATOR_DEPS}
  COMMAND ${CMAKE_COMMAND} -E make_directory ${INTERP_OUT_DIR}
  COMMAND ${CMAKE_COMMAND} -E env
          "PYTHONPATH=${CMAKE_SOURCE_DIR}"
          ${Python3_EXECUTABLE}
          ${INTERPRETER_SOURCE_DIR}/main.py
          --ir-path ${CMAKE_SOURCE_DIR}/data/${ARCH_TARGET}/RV32I.yaml
          --out-dir ${INTERP_OUT_DIR}
  COMMENT "Generating LIRA interpreter sources"
)

add_custom_target(gen-interp DEPENDS ${INTERP_GENERATED})

set(INTERP_RUNTIME_DIR "${INTERPRETER_SOURCE_DIR}/runtime")

add_executable(sim-interp
  ${INTERP_OUT_DIR}/decoder.cc
  ${INTERP_OUT_DIR}/snippets.cc
  ${INTERP_OUT_DIR}/base_ops.cc
  ${INTERP_OUT_DIR}/naive_interpreter.cc
  ${INTERP_RUNTIME_DIR}/base_exec_engine.cc
  ${INTERP_RUNTIME_DIR}/hart.cc
  ${INTERP_RUNTIME_DIR}/memory.cc
  ${INTERP_RUNTIME_DIR}/elf_loader.cc
  ${INTERP_OUT_DIR}/cpu_state.cc
  ${INTERP_RUNTIME_DIR}/Target/RISC_V/cpu_state_ext.cc
  ${INTERP_RUNTIME_DIR}/sim.cc
)
set_target_properties(sim-interp PROPERTIES
  OUTPUT_NAME interpreter
  RUNTIME_OUTPUT_DIRECTORY "${INTERP_OUT_DIR}")

target_include_directories(sim-interp PRIVATE
  ${INTERP_OUT_DIR}
  ${INTERP_RUNTIME_DIR}
)

target_link_libraries(sim-interp PRIVATE elfio CLI11 fmt)
target_compile_features(sim-interp PRIVATE cxx_std_20)

add_custom_target(build-interp DEPENDS sim-interp)
