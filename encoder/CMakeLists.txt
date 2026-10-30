# Code generation of the instruction encoder

set(ENCODER_OUT_DIR "${CMAKE_BINARY_DIR}/encoder"
    CACHE PATH "Directory for the generated encoder sources")

lira_add_generator(encoder ${CMAKE_CURRENT_LIST_DIR}/main.py ${ENCODER_OUT_DIR}
  isa.hh encoder.hh encoder.cc
)

add_library(encoder STATIC ${ENCODER_OUT_DIR}/encoder.cc)

target_include_directories(encoder PUBLIC
  ${ENCODER_OUT_DIR}
)
target_compile_features(encoder PUBLIC cxx_std_20)
target_link_libraries(encoder PUBLIC snippets)

add_dependencies(encoder gen-encoder gen-snippets gen-ir)

add_custom_target(build-encoder DEPENDS encoder)
