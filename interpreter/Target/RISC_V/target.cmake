set(TARGET_IR ${CMAKE_SOURCE_DIR}/data/RISC_V/RV32I.yaml)
set(TARGET_RUNTIME_SOURCES
  ${INTERP_RUNTIME_DIR}/Target/RISC_V/cpu_state_ext.cc
  ${INTERP_RUNTIME_DIR}/Target/RISC_V/riscv_elf_loader.cc
)
set(TARGET_SIM_MAIN ${INTERP_RUNTIME_DIR}/Target/RISC_V/sim.cc)
