set(FORMATTER_OUT_DIR "${CMAKE_BINARY_DIR}/format"
    CACHE PATH "Directory for the generated formatter sources")

lira_add_generator(formatter ${CMAKE_CURRENT_LIST_DIR}/main.py ${FORMATTER_OUT_DIR}
  isa.hh formatter.hh formatter.cc
)

add_library(formatter STATIC ${FORMATTER_OUT_DIR}/formatter.cc)
target_include_directories(formatter PUBLIC ${FORMATTER_OUT_DIR})
target_compile_features(formatter PUBLIC cxx_std_20)
add_dependencies(formatter gen-formatter)

add_custom_target(build-formatter DEPENDS formatter)
