# Code generation of the instruction decoder

set(DECODER_OUT_DIR "${CMAKE_BINARY_DIR}/decoder"
    CACHE PATH "Directory for the generated decoder sources")

lira_add_generator(decoder ${CMAKE_CURRENT_LIST_DIR}/main.py ${DECODER_OUT_DIR}
  isa.hh decoder.hh decoder.cc
)

add_library(decoder STATIC ${DECODER_OUT_DIR}/decoder.cc)
target_include_directories(decoder PUBLIC ${DECODER_OUT_DIR})
target_compile_features(decoder PUBLIC cxx_std_20)
target_link_libraries(decoder PUBLIC snippets)

add_dependencies(decoder gen-decoder gen-snippets gen-ir)

add_custom_target(build-decoder DEPENDS decoder)
