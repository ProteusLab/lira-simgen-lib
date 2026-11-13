lira_add_generator(decoder decoder.main decoder.cc)
add_library(decoder STATIC decoder.cc)
add_dependencies(decoder gen-decoder)
target_compile_features(decoder PUBLIC cxx_std_20)
