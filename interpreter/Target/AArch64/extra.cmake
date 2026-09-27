# Single-instruction C API over host memory, used to test the generated
# interpreter instruction by instruction (see runtime/Target/AArch64/c_api.cc).
add_library(a64-capi SHARED ${INTERP_RUNTIME_DIR}/Target/AArch64/c_api.cc)
target_link_libraries(a64-capi PRIVATE interp-core)
set_target_properties(a64-capi PROPERTIES
  LIBRARY_OUTPUT_DIRECTORY "${INTERP_OUT_DIR}")
