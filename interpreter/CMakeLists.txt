lira_add_generator(interp interpreter.main
  cpu_state.hh cpu_state.cc naive_interpreter.hh naive_interpreter.cc)

option(LIRA_INTERPRETER_CLI "Build the ELF-running interpreter executable" ON)

include(FetchContent)
FetchContent_Declare(fmt
  GIT_REPOSITORY https://github.com/fmtlib/fmt.git
  GIT_TAG 12.0.0)
FetchContent_MakeAvailable(fmt)

set(runtime "${CMAKE_CURRENT_SOURCE_DIR}/runtime")
set(target_runtime "${runtime}/Target/${ARCH_TARGET}")
add_library(interp-core STATIC
  cpu_state.cc
  naive_interpreter.cc
  "${runtime}/base_exec_engine.cc"
  "${runtime}/memory.cc"
  "${target_runtime}/cpu_state_ext.cc")
add_dependencies(interp-core gen-interp)
target_include_directories(interp-core PUBLIC
  "${CMAKE_CURRENT_BINARY_DIR}"
  "${runtime}"
  "${target_runtime}")
target_link_libraries(interp-core PUBLIC decoder PRIVATE fmt::fmt-header-only)

add_custom_target(build-interp DEPENDS interp-core)

if(ARCH_TARGET STREQUAL "AArch64")
  set_target_properties(interp-core decoder base_ops PROPERTIES POSITION_INDEPENDENT_CODE ON)
  add_library(a64-capi SHARED "${target_runtime}/c_api.cc")
  target_link_libraries(a64-capi PRIVATE interp-core)
  add_dependencies(build-interp a64-capi)
endif()

if(LIRA_INTERPRETER_CLI)
  FetchContent_Declare(elfio
    GIT_REPOSITORY https://github.com/serge1/ELFIO.git
    GIT_TAG Release_3.12)
  FetchContent_Declare(cli11
    GIT_REPOSITORY https://github.com/CLIUtils/CLI11.git
    GIT_TAG v2.5.0)
  FetchContent_MakeAvailable(elfio cli11)

  string(TOLOWER "${ARCH_TARGET}" target_name)
  string(REPLACE "_" "" target_name "${target_name}")
  add_executable(sim-interp
    "${runtime}/elf_loader.cc"
    "${runtime}/hart.cc"
    "${target_runtime}/${target_name}_elf_loader.cc"
    "${target_runtime}/sim.cc")
  target_link_libraries(sim-interp PRIVATE interp-core elfio::elfio CLI11::CLI11 fmt::fmt)
  set_target_properties(sim-interp PROPERTIES OUTPUT_NAME interpreter)
  add_dependencies(build-interp sim-interp)
endif()
