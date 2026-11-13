lira_add_generator(formatter format.main formatter.cc)
add_library(formatter STATIC formatter.cc)
add_dependencies(formatter gen-formatter)
target_compile_features(formatter PUBLIC cxx_std_20)
