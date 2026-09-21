if(NOT DEFINED SAIL_SIM OR NOT DEFINED BASE_CONFIG OR NOT DEFINED OVERRIDE_CONFIG)
    message(FATAL_ERROR "SAIL_SIM, BASE_CONFIG, and OVERRIDE_CONFIG are required")
endif()

execute_process(
    COMMAND "${SAIL_SIM}"
        --validate-config
        --config "${BASE_CONFIG}"
        --config-override "${OVERRIDE_CONFIG}"
    RESULT_VARIABLE status
    OUTPUT_VARIABLE stdout
    ERROR_VARIABLE stderr
)

if(status EQUAL 0)
    message(FATAL_ERROR "shared backend configuration unexpectedly passed validation")
endif()

set(output "${stdout}\n${stderr}")
if(NOT output MATCHES "extensions\\.Ztt\\.ame_backend=shared is not supported")
    message(FATAL_ERROR "validation failed for an unexpected reason:\n${output}")
endif()
