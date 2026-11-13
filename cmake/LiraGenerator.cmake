function(lira_add_generator name module)
  set(outputs)
  foreach(file IN LISTS ARGN)
    list(APPEND outputs "${CMAKE_CURRENT_BINARY_DIR}/${file}")
  endforeach()

  file(GLOB_RECURSE sources CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/*.py"
    "${CMAKE_CURRENT_SOURCE_DIR}/*.jinja"
    "${PROJECT_SOURCE_DIR}/shared/*.py")
  set(ir_args)
  if(LIRA_IR_FILE)
    list(APPEND ir_args --ir-path "${LIRA_IR_FILE}")
  endif()

  add_custom_command(
    OUTPUT ${outputs}
    COMMAND "${Python3_EXECUTABLE}" -B -m "${module}"
      --arch-target "${ARCH_TARGET}"
      --out-dir "${CMAKE_CURRENT_BINARY_DIR}"
      ${ir_args}
    DEPENDS ${sources} ${LIRA_IR_FILE}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    VERBATIM)
  add_custom_target(gen-${name} ALL DEPENDS ${outputs})
endfunction()
