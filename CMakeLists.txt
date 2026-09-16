cmake_minimum_required(VERSION 3.22 FATAL_ERROR)

project(lira-simgen-lib
  VERSION 0.1.0
  DESCRIPTION "LIRA-driven simulator generator framework"
  LANGUAGES NONE)

include(cmake/CPM.cmake)

CPMAddPackage(
  NAME LIRA
  GITHUB_REPOSITORY ProteusLab/LIRA
  GIT_TAG c488727a3da3d87c1ee96d03f37003088952528a
)

# Target architecture: selects the data/${ARCH_TARGET} directory with
# the LIRA IR inputs.
set(ARCH_TARGET "RISC_V" CACHE STRING "Target architecture (data directory)")

install(FILES data/${ARCH_TARGET}/RV32I.yaml
        DESTINATION share/lira-simgen-lib/${ARCH_TARGET})

add_subdirectory(interpreter)
