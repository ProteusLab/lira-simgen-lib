# lira-simgen-lib/interpreter/CMakeLists.txt

set(INTERPRETER_SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}")

lira_add_generator(interp ${INTERPRETER_SOURCE_DIR}/main.py ${INTERP_OUT_DIR}
  execute.hh execute.cc cpu_state.hh cpu_state.cc
)

add_executable(interp
  ${INTERP_OUT_DIR}/execute.cc
  ${INTERP_OUT_DIR}/cpu_state.cc
)
set_target_properties(interp PROPERTIES
  OUTPUT_NAME interpreter
  RUNTIME_OUTPUT_DIRECTORY "${INTERP_OUT_DIR}")

target_include_directories(interp PRIVATE
  ${INTERP_OUT_DIR}
)

target_link_libraries(interp PRIVATE
  runtime
)
target_compile_features(interp PRIVATE cxx_std_20)

add_dependencies(interp gen-interp gen-decoder gen-base_ops gen-ir)

add_custom_target(build-interp DEPENDS interp)

add_subdirectory(runtime)
