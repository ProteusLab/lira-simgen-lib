cmake_minimum_required(VERSION 3.22 FATAL_ERROR)

project(lira-simgen-lib
  VERSION 0.1.0
  DESCRIPTION "LIRA-driven simulator generator framework"
  LANGUAGES CXX)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(ARCH_TARGET "RISC_V" CACHE STRING "Target architecture")
set(LIRA_IR_FILE "" CACHE FILEPATH "LIRA architecture YAML for base operations")

include(cmake/LiraGenerator.cmake)

add_subdirectory(shared)
add_subdirectory(encoder)
add_subdirectory(decoder)
add_subdirectory(format)
