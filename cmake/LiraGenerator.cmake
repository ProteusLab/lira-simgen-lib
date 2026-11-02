function(lira_add_generator name script out_dir)
  set(outputs)

  foreach(file IN LISTS ARGN)
    list(APPEND outputs "${out_dir}/${file}")
  endforeach()

  separate_arguments(script_args NATIVE_COMMAND "${script}")

  add_custom_command(
    OUTPUT ${outputs}
    DEPENDS ${GENERATOR_DEPS} ${LIRA_IR_FILE}
    COMMAND ${CMAKE_COMMAND} -E make_directory ${out_dir}
    COMMAND ${GENERATOR_ENV} ${Python3_EXECUTABLE} ${script_args}
      --ir-path ${LIRA_IR_FILE}
      --arch-target ${ARCH_TARGET}
      --out-dir ${out_dir}
    COMMENT "Generating ${name} sources"
  )

  add_custom_target(gen-${name} DEPENDS ${outputs} gen-ir)

  endfunction()
