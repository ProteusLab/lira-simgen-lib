lira_add_generator(isa shared.isa isa.hh)
lira_add_generator(base-ops shared.base_ops base_ops.hh base_ops.cc)
add_library(base_ops STATIC base_ops.cc)
add_dependencies(base_ops gen-base-ops gen-isa)
target_include_directories(base_ops PUBLIC
  "${CMAKE_CURRENT_BINARY_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/runtime")
target_compile_features(base_ops PUBLIC cxx_std_20)
