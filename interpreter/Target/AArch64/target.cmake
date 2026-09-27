set(TARGET_IR ${CMAKE_SOURCE_DIR}/data/AArch64/aarch64.yaml)
set(TARGET_RUNTIME_SOURCES
  ${INTERP_RUNTIME_DIR}/Target/AArch64/cpu_state_ext.cc
  ${INTERP_RUNTIME_DIR}/Target/AArch64/aarch64_elf_loader.cc
)
set(TARGET_SIM_MAIN ${INTERP_RUNTIME_DIR}/Target/AArch64/sim.cc)
