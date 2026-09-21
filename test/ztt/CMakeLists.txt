# Ztt build support: regenerate the Sail model and GAS macros from the manual
# snapshot and keep them synchronized.  Test generation, compilation, and
# execution live in run_ztt_tests.py, which also owns the N/UDS/M/ACC matrix
# and the per-combo runtime configurations.

find_program(RUBY_BIN "ruby")

if (NOT RUBY_BIN)
    message(FATAL_ERROR "ENABLE_RISCV_ZTT_TESTS requires ruby for Ztt artifact generation")
endif()

set(ZTT_SAIL_MODEL_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../model/extensions/Ztt")
set(ZTT_GENERATED_MACROS "${CMAKE_CURRENT_SOURCE_DIR}/src/ame_macros.inc")

file(GLOB_RECURSE ztt_machine_readable_sources CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/manual-main/*"
    "${CMAKE_CURRENT_SOURCE_DIR}/generators/*"
)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    ${ztt_machine_readable_sources}
)

execute_process(
    COMMAND ${RUBY_BIN} "${CMAKE_CURRENT_SOURCE_DIR}/generators/gen_ztt_sail.rb"
        --output-dir "${ZTT_SAIL_MODEL_DIR}"
    RESULT_VARIABLE ztt_sail_generation_status
    ERROR_VARIABLE ztt_sail_generation_error
)
if (NOT ztt_sail_generation_status EQUAL 0)
    message(FATAL_ERROR "Failed to generate Ztt Sail model:\n${ztt_sail_generation_error}")
endif()
execute_process(
    COMMAND ${RUBY_BIN} "${CMAKE_CURRENT_SOURCE_DIR}/generators/gen_ztt_macros.rb"
    OUTPUT_FILE "${ZTT_GENERATED_MACROS}"
    RESULT_VARIABLE ztt_macro_status
    ERROR_VARIABLE ztt_macro_error
)
if (NOT ztt_macro_status EQUAL 0)
    message(FATAL_ERROR "Failed to generate Ztt macros:\n${ztt_macro_error}")
endif()

set(ZTT_INSTRUCTION_DATA "${CMAKE_CURRENT_SOURCE_DIR}/manual-main/instructions.json" CACHE FILEPATH
    "Ztt instruction snapshot for optional manual synchronization checks")
set(ZTT_EXPECTED_MACROS "${ZTT_GENERATED_MACROS}" CACHE FILEPATH
    "Ztt macro include generated from ZTT_INSTRUCTION_DATA for encoding-level validation")

if (ZTT_EXPECTED_MACROS AND NOT ZTT_INSTRUCTION_DATA)
    message(FATAL_ERROR "ZTT_EXPECTED_MACROS requires ZTT_INSTRUCTION_DATA")
endif()

if (ZTT_INSTRUCTION_DATA)
    find_program(ZTT_PYTHON3_BIN "python3")
    if (NOT ZTT_PYTHON3_BIN)
        message(FATAL_ERROR "ZTT_INSTRUCTION_DATA requires python3")
    endif()

    set(ztt_manual_sync_command
        ${ZTT_PYTHON3_BIN} "${CMAKE_CURRENT_SOURCE_DIR}/gen/check_manual_sync.py"
        --instruction-data "${ZTT_INSTRUCTION_DATA}"
        --sail-model "${CMAKE_CURRENT_SOURCE_DIR}/../../model/extensions/Ztt"
        --strict
    )
    if (ZTT_EXPECTED_MACROS)
        list(APPEND ztt_manual_sync_command --expected-macros "${ZTT_EXPECTED_MACROS}")
    endif()

    execute_process(
        COMMAND ${ztt_manual_sync_command}
        RESULT_VARIABLE ztt_manual_sync_status
        OUTPUT_VARIABLE ztt_manual_sync_output
        ERROR_VARIABLE ztt_manual_sync_error
    )
    if (NOT ztt_manual_sync_status EQUAL 0)
        message(FATAL_ERROR
            "Ztt test inputs are out of sync with ${ZTT_INSTRUCTION_DATA}:\n"
            "${ztt_manual_sync_output}${ztt_manual_sync_error}"
        )
    endif()
endif()
