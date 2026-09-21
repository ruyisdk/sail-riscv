set(generated_config_filenames)
set(CONFIG__ZTT__NLEN_POW 3)
set(CONFIG__ZTT__UNIT_DTYPE_SIZE_POW 3)
set(CONFIG__ZTT__BACKEND "dedicated")
# These implementation parameters are passed through to config.json.in and
# are also consumed by the generated Ztt test suite.
set(CONFIG__ZTT__NUM_M_REGS 32 CACHE STRING
    "Number of AME M/Md registers (16 or 32)")
set_property(CACHE CONFIG__ZTT__NUM_M_REGS PROPERTY STRINGS 16 32)
set(CONFIG__ZTT__NUM_ACC_REGS 4 CACHE STRING
    "Number of AME Acc/Ad registers (1, 2, 4, 8, or 16)")
set_property(CACHE CONFIG__ZTT__NUM_ACC_REGS PROPERTY STRINGS 1 2 4 8 16)

# Create a variety of configuration files for different XLEN/ELEN/VLENs.
foreach(CONFIG__BASE__XLEN IN ITEMS 32 64)
    foreach(CONFIG__V__ELEN_EXP RANGE 5 6)
        foreach(CONFIG__V__VLEN_EXP RANGE 6 9)
            math(EXPR vlen "1 << ${CONFIG__V__VLEN_EXP}")
            math(EXPR elen "1 << ${CONFIG__V__ELEN_EXP}")

            set(config_filename "rv${CONFIG__BASE__XLEN}d_v${vlen}_e${elen}.json")

            set(CONFIG_XLEN_IS_32 "false")
            set(CONFIG_XLEN_IS_64 "false")
            set(CONFIG_XLEN_IS_${CONFIG__BASE__XLEN} "true")

            if (${CONFIG__BASE__XLEN} EQUAL 32)
              set(CONFIG_MIDELEG_DELEGATABLE_BITS_VALUE "0x0000_2222")
            else()
              set(CONFIG_MIDELEG_DELEGATABLE_BITS_VALUE "0x0000_0000_0000_2222")
            endif()

            set(CONFIG_ELEN_IS_32 "false")
            set(CONFIG_ELEN_IS_64 "false")
            set(CONFIG_ELEN_IS_${elen} "true")

            if(CONFIG_ELEN_IS_32 STREQUAL true)
              set(CONFIG__V__SUPPORT "Float_single")
            # Check if we can enable the full V extension.
            elseif((CONFIG_ELEN_IS_64 STREQUAL true) AND (vlen GREATER 64))
              set(CONFIG__V__SUPPORT "Full")
            # Otherwise fallback to Float_double for ELEN=64.
            elseif(CONFIG_ELEN_IS_64 STREQUAL true)
              set(CONFIG__V__SUPPORT "Float_double")
            endif()

            if(CONFIG_XLEN_IS_32 STREQUAL true)
                set(CONFIG__PHYSADDR__BITS 34)
                set(CONFIG__ASID__LEN 9)
                set(CONFIG__VMID__LEN 7)
            elseif(CONFIG_XLEN_IS_64 STREQUAL true)
                set(CONFIG__PHYSADDR__BITS 56)
                set(CONFIG__ASID__LEN 16)
                set(CONFIG__VMID__LEN 14)
            endif()

            # GEILEN is at most XLEN-1.
            math(EXPR CONFIG__H__GEILEN "${CONFIG__BASE__XLEN} - 1")

            configure_file(config.json.in ${CMAKE_CURRENT_BINARY_DIR}/${config_filename})

            install(FILES ${CMAKE_CURRENT_BINARY_DIR}/${config_filename}
                DESTINATION ${CMAKE_INSTALL_DATADIR}/${CMAKE_PROJECT_NAME}/config
            )

            list(APPEND generated_config_filenames "${CMAKE_CURRENT_BINARY_DIR}/${config_filename}")
        endforeach()
    endforeach()
endforeach()

# Generate focused Ztt configurations from the same runtime template.  The
# generated instruction suites use the N=8 variants, while the other square
# sizes are consumed by the runtime-dynamic configuration smoke. The matrix
# covers the UDS values whose packed operand formation differs.
set(CONFIG__BASE__XLEN 64)
set(CONFIG__V__ELEN_EXP 6)
set(CONFIG__V__VLEN_EXP 8)
set(CONFIG_XLEN_IS_32 "false")
set(CONFIG_XLEN_IS_64 "true")
set(CONFIG_ELEN_IS_32 "false")
set(CONFIG_ELEN_IS_64 "true")
set(CONFIG__V__SUPPORT "Full")

foreach(CONFIG__ZTT__NLEN_POW IN ITEMS 2 3 4 5)
    math(EXPR ztt_nlen "1 << ${CONFIG__ZTT__NLEN_POW}")
    foreach(CONFIG__ZTT__UNIT_DTYPE_SIZE_POW IN ITEMS 3 4 5)
        math(EXPR ztt_uds "1 << ${CONFIG__ZTT__UNIT_DTYPE_SIZE_POW}")
        set(config_filename
            "rv64d_v256_e64_ztt_n${ztt_nlen}_u${ztt_uds}.json")
        configure_file(config.json.in ${CMAKE_CURRENT_BINARY_DIR}/${config_filename})

        install(FILES ${CMAKE_CURRENT_BINARY_DIR}/${config_filename}
            DESTINATION ${CMAKE_INSTALL_DATADIR}/${CMAKE_PROJECT_NAME}/config
        )

        list(APPEND generated_config_filenames
            "${CMAKE_CURRENT_BINARY_DIR}/${config_filename}")
    endforeach()
endforeach()

# Make list of config files visible to c_emulator build.
set(generated_config_filenames "${generated_config_filenames}" PARENT_SCOPE)

# Embed the default configs in a C header.
file(READ "${CMAKE_CURRENT_BINARY_DIR}/rv64d_v256_e64.json" DEFAULT_JSON)
file(READ "${CMAKE_CURRENT_BINARY_DIR}/rv32d_v256_e64.json" DEFAULT_JSON_RV32)
configure_file("default_config.h.in" "default_config.h" @ONLY)

add_library(default_config INTERFACE
    "default_config.h"
)

target_include_directories(default_config INTERFACE "${CMAKE_CURRENT_BINARY_DIR}")
