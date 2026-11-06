# Converts the native Protea IR into LIRA IR.

set(NATIVE_IR_FILE "${protea_irgen_BINARY_DIR}/IR.yaml")

file(GLOB_RECURSE PROTEA_ADL_DEPS CONFIGURE_DEPENDS
  "${protea_SOURCE_DIR}/lib/*.rb"
)

file(GLOB_RECURSE CONVERTER_DEPS CONFIGURE_DEPENDS
  "${CMAKE_CURRENT_LIST_DIR}/*.py"
)

set(LIRA_IR_OUTPUT "${ARCH_TARGET}.yaml")
set(LIRA_IR_FILE "${LIRA_IR_DIR}/${LIRA_IR_OUTPUT}")

set(LIRA_IR_FILE "${LIRA_IR_FILE}" PARENT_SCOPE)

add_custom_command(
  OUTPUT ${LIRA_IR_FILE}
  DEPENDS protea_irgen ${PROTEA_ADL_DEPS} ${CONVERTER_DEPS}
  COMMAND ${CMAKE_COMMAND} -E make_directory ${LIRA_IR_DIR}
  COMMAND ${GENERATOR_ENV}
    ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_LIST_DIR}/main.py
    --ir-path ${NATIVE_IR_FILE}
    --output ${LIRA_IR_FILE}
  COMMENT "Converting the native Protea IR to LIRA IR (${LIRA_IR_OUTPUT})"
)

add_custom_target(gen-ir DEPENDS ${LIRA_IR_FILE})
