# Fetches the Protea ADL sources

if(NOT ARCH_TARGET STREQUAL "RISC_V")
  message(FATAL_ERROR
    "ARCH_SOURCE=Protea currently supports only ARCH_TARGET=RISC_V "
    "(got '${ARCH_TARGET}')")
endif()

CPMAddPackage(
  NAME protea
  GITHUB_REPOSITORY ProteusLab/Protea
  GIT_TAG lira-tools-integration
  OPTIONS "PROTEA_BUILD_SIM OFF" 
          "PROTEA_USE_BUNDLER OFF"
)
