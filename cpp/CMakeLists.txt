# lira-simgen-lib/cpp/CMakeLists.txt

set(CPP_OUT_DIR "${CMAKE_BINARY_DIR}/cpp"
    CACHE PATH "Directory for the generated shared support sources")

lira_add_generator(base_ops "-m cpp.base_ops" ${CPP_OUT_DIR}
  base_ops.hh base_ops.cc
)

add_library(base_ops STATIC ${CPP_OUT_DIR}/base_ops.cc)
target_include_directories(base_ops PUBLIC ${CPP_OUT_DIR})
target_compile_features(base_ops PUBLIC cxx_std_20)

add_dependencies(base_ops gen-ir)
