# lira-simgen-lib/interpreter/runtime/CMakeLists.txt

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

set(RUNTIME_SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}")

file(GLOB RUNTIME_TARGET_SOURCES CONFIGURE_DEPENDS
  "${RUNTIME_SOURCE_DIR}/Target/${ARCH_TARGET}/*.cc"
)

add_library(runtime STATIC
  ${RUNTIME_SOURCE_DIR}/base_exec_engine.cc
  ${RUNTIME_SOURCE_DIR}/hart.cc
  ${RUNTIME_SOURCE_DIR}/memory.cc
  ${RUNTIME_SOURCE_DIR}/elf_loader.cc
  ${RUNTIME_TARGET_SOURCES}
)

target_include_directories(runtime PUBLIC
  ${RUNTIME_SOURCE_DIR}
  ${INTERP_OUT_DIR}
)

target_link_libraries(runtime PUBLIC
  decoder
  elfio
  CLI11
  fmt
)
target_compile_features(runtime PUBLIC cxx_std_20)

add_dependencies(runtime gen-interp gen-decoder gen-ir)

add_custom_target(build-runtime DEPENDS runtime)
