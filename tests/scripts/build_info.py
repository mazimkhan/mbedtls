import os

def check_no_udbl():
    ret = os.system("grep __aeabi_uldiv library/*.o")
    return (ret != 0)

data = {
    "builds": {
        "make-gcc": {
            "build": "make",
            "environment": {"MAKE": "make", "CC": "gcc"},
            "tests": ["make test", "./programs/test/selftest"]
        },
        "unix-make": {
            "build": "make",
            "environment": {"MAKE": "make", "CC": "gcc", "CFLAGS": "-Werror -Wall -Wextra -Os"}
        },
        "make-no-std-func-nv-seed": {
            "config": {
                "config": "full",
                "set": ["MBEDTLS_PLATFORM_NO_STD_FUNCTIONS"],
                "unset": ["MBEDTLS_ENTROPY_NV_SEED"]
            },
            "build": "make",
            "environment": {"MAKE": "make", "CC": "gcc", "CFLAGS": "-Werror -Wall -Wextra -O0"}
        },
        "make-no-srv": {
            "config": {"config": "full", "unset": ["MBEDTLS_SSL_SRV_C"]},
            "build": "make",
            "environment": {"MAKE": "make", "CC": "gcc", "CFLAGS": "-Werror -Wall -Wextra -O0"}
        },
        "make-no-client": {
            "config": {"config": "full", "unset": ["MBEDTLS_SSL_CLI_C"]},
            "build": "make",
            "environment": {"MAKE": "make", "CC": "gcc", "CFLAGS": "-Werror -Wall -Wextra -O0"}
        },
        "make-no-net-entropy": {
            "config": {
                "config": "full",
                "set": ["MBEDTLS_NO_PLATFORM_ENTROPY"],
                "unset": ["MBEDTLS_NET_C"]
            },
            "build": "make",
            "environment": {"MAKE": "make", "CC": "gcc", "MAKE_TARGET": "lib", "CFLAGS": "-Werror -Wall -Wextra -O0 -std=c99 -pedantic"}
        },
        "make-full-config": {
            "config": {
                "config": "full",
                "unset": [
                    "MBEDTLS_PLATFORM_C",
                    "MBEDTLS_NET_C",
                    "MBEDTLS_PLATFORM_MEMORY",
                    "MBEDTLS_PLATFORM_PRINTF_ALT",
                    "MBEDTLS_PLATFORM_FPRINTF_ALT",
                    "MBEDTLS_PLATFORM_SNPRINTF_ALT",
                    "MBEDTLS_PLATFORM_TIME_ALT",
                    "MBEDTLS_PLATFORM_EXIT_ALT",
                    "MBEDTLS_ENTROPY_NV_SEED",
                    "MBEDTLS_MEMORY_BUFFER_ALLOC_C",
                    "MBEDTLS_FS_IO"
                ]
            },
            "build": "make",
            "environment": {"MAKE": "make", "CC": "gcc",
                "CFLAGS": "-Werror -Wall -Wextra -O0 -std=c99 -pedantic -D_DEFAULT_SOURCE"},
            "tests": ["make test", "./programs/test/selftest"]
        },
        "make-shared": {
            "build": "make",
            "environment": {"MAKE": "make", "CC": "gcc", "SHARED": "1"}
        },
        "make-i386-on-x64": {
            "build": "make",
            "environment": {"MAKE": "make", "CC": "gcc", "CFLAGS": "-Werror -Wall -Wextra -m32"},
            "tests": ["make test", "./programs/test/selftest"]
        },
        "make-ilp32-on-x64": {
            "build": "make",
            "environment": {"MAKE": "make", "CC": "gcc", "CFLAGS": "-Werror -Wall -Wextra -mx32"},
            "tests": ["make test", "./programs/test/selftest"]
        },
        "make-32bit-bignum-limbs": {
            "config": {"unset": ["MBEDTLS_HAVE_ASM", "MBEDTLS_AESNI_C", "MBEDTLS_PADLOCK_C"]},
            "build": "make",
            "environment": {"MAKE": "make", "CC": "gcc",
                            "CFLAGS": "-Werror -Wall -Wextra -DMBEDTLS_HAVE_INT32"},
            "tests": ["make test", "./programs/test/selftest"]
        },
        "make-64bit-bignum-limbs": {
            "config": {"unset": ["MBEDTLS_HAVE_ASM", "MBEDTLS_AESNI_C", "MBEDTLS_PADLOCK_C"]},
            "build": "make",
            "environment": {"MAKE": "make", "CC": "gcc",
                            "CFLAGS": "-Werror -Wall -Wextra -DMBEDTLS_HAVE_INT64"},
            "tests": ["make test", "./programs/test/selftest"]
        },
        "make-gcc-arm": {
            "config": {"config": "baremetal"},
            "build": "make",
            "environment": {"MAKE": "make", "CC": "arm-none-eabi-gcc",
                            "AR": "arm-none-eabi-ar", "LD": "arm-none-eabi-ld",
                            "CFLAGS": "-Werror -Wall -Wextra",
                            "MAKE_TARGET": "lib"}
        },
        "make-gcc-arm-no-udbl": {
            "config": {"config": "baremetal", "set": ["MBEDTLS_NO_UDBL_DIVISION"]},
            "build": "make",
            "environment": {"MAKE": "make", "CC": "arm-none-eabi-gcc",
                            "AR": "arm-none-eabi-ar", "LD": "arm-none-eabi-ld",
                            "CFLAGS": "-Werror -Wall -Wextra",
                            "MAKE_TARGET": "lib"},
            "tests": [check_no_udbl]
        },
        "make-arm5": {
            "config": {"config": "baremetal"},
            "build": "make",
            "environment": {"MAKE": "make", "CC": "$ARMC5_BIN_DIR/armcc",
                            "AR": "$ARMC5_BIN_DIR/armar",
                            "WARNING_CFLAGS": "--strict --c99",
                            "MAKE_TARGET": "lib"},
            "requires": ["armc5"]
        },
        "make-arm6-v7-a": {
            "config": {"config": "baremetal"},
            "build": "make",
            "environment": {"MAKE": "make", "CC": "$ARMC6_BIN_DIR/armclang",
                            "ARM_TOOL_VARIANT": "ult",
                            "AR": "$ARMC6_BIN_DIR/armar",
                            "WARNING_CFLAGS": "-xc -std=c99",
                            "CFLAGS": "--target=arm-arm-none-eabi -march=armv7-a",
                            "MAKE_TARGET": "lib"},
            "requires": ["armc6"]
        },
        "make-arm6-v7-m": {
            "config": {"config": "baremetal"},
            "build": "make",
            "environment": {"MAKE": "make", "CC": "$ARMC6_BIN_DIR/armclang",
                            "ARM_TOOL_VARIANT": "ult",
                            "AR": "$ARMC6_BIN_DIR/armar",
                            "WARNING_CFLAGS": "-xc -std=c99",
                            "CFLAGS": "--target=arm-arm-none-eabi -march=armv7-m",
                            "MAKE_TARGET": "lib"},
            "requires": ["armc6"]
        },
        "make-arm6-v8.2-a": {
            "config": {"config": "baremetal"},
            "build": "make",
            "environment": {"MAKE": "make", "CC": "$ARMC6_BIN_DIR/armclang",
                            "ARM_TOOL_VARIANT": "ult",
                            "AR": "$ARMC6_BIN_DIR/armar",
                            "WARNING_CFLAGS": "-xc -std=c99",
                            "CFLAGS": "--target=arm-arm-none-eabi -march=armv8.2-a",
                            "MAKE_TARGET": "lib"},
            "requires": ["armc6"]
        },
        "make-arm6-v8.2-a-64bit": {
            "config": {"config": "baremetal"},
            "build": "make",
            "environment": {"MAKE": "make", "CC": "$ARMC6_BIN_DIR/armclang",
                            "ARM_TOOL_VARIANT": "ult",
                            "AR": "$ARMC6_BIN_DIR/armar",
                            "WARNING_CFLAGS": "-xc -std=c99",
                            "CFLAGS": "--target=aarch64-arm-none-eabi -march=armv8.2-a",
                            "MAKE_TARGET": "lib"},
            "requires": ["armc6"]
        },
        "make-arm6-v8-m.main": {
            "config": {"config": "baremetal"},
            "build": "make",
            "environment": {"MAKE": "make", "CC": "$ARMC6_BIN_DIR/armclang",
                            "ARM_TOOL_VARIANT": "ult",
                            "AR": "$ARMC6_BIN_DIR/armar",
                            "WARNING_CFLAGS": "-xc -std=c99",
                            "CFLAGS": "--target=arm-arm-none-eabi -march=armv8-m.main",
                            "MAKE_TARGET": "lib"},
            "requires": ["armc6"]
        },
        "make-allow-sha1-certs": {
            "config": {"set": ["MBEDTLS_TLS_DEFAULT_ALLOW_SHA1_IN_CERTIFICATES"]},
            "build": "make",
            "environment": {"MAKE": "make", "CC": "gcc", "CFLAGS": "-Werror -Wall -Wextra"},
            "tests": ["make test", "./programs/test/selftest", "./tests/ssl-opt.sh -f \"SHA-1\""]
        },
        "cross-build-windows": {
            "build": "make",
            "environment": {"MAKE": "make", "CC": "i686-w64-mingw32-gcc",
                            "AR": "i686-w64-mingw32-ar", "LD": "i686-w64-minggw32-ld",
                            "CFLAGS": "-Werror -Wall -Wextra", "WINDOWS_BUILD": "1",
                            "MAKE_TARGET": "lib programs"}
        },
        "cross-build-tests-windows": {
            "build": "make",
            "environment": {"MAKE": "make", "CC": "i686-w64-mingw32-gcc",
                            "AR": "i686-w64-mingw32-ar", "LD": "i686-w64-minggw32-ld",
                            "CFLAGS": "-Werror", "WINDOWS_BUILD": "1"}
        },
        "cross-build-dll": {
            "build": "make",
            "environment": {"MAKE": "make", "CC": "i686-w64-mingw32-gcc",
                            "AR": "i686-w64-mingw32-ar", "LD": "i686-w64-minggw32-ld",
                            "CFLAGS": "-Werror -Wall -Wextra", "WINDOWS_BUILD": "1",
                            "SHARED": "1", "MAKE_TARGET": "lib programs"}
        },
        "cross-build-tests-dll": {
            "build": "make",
            "environment": {"MAKE": "make", "CC": "i686-w64-mingw32-gcc",
                            "AR": "i686-w64-mingw32-ar", "LD": "i686-w64-minggw32-ld",
                            "CFLAGS": "-Werror", "WINDOWS_BUILD": "1",
                            "SHARED": "1"}
        },
        "cmake": {
            "build": "cmake",
            "environment": {"MAKE": "make", "CC": "gcc", "CMAKE_BUILD_TYPE": "Check"},
            "tests": ["make test", "./programs/test/selftest"]
        },
        "cmake-full":  {
            "build": "cmake",
            "environment": {"MAKE": "make", "CC": "gcc", "CMAKE_BUILD_TYPE": "Check"},
            "tests": ["full"]
        },
        "cmake-asan": {
            "build": "cmake",
            "environment": {"MAKE": "make", "CC": "clang", "CMAKE_BUILD_TYPE": "ASan"},
            "tests": ["full"]
        },
        "cmake-asan-gcc": {
            "build": "cmake",
            "environment": {"MAKE": "make", "CC": "gcc", "CMAKE_BUILD_TYPE": "ASan"},
            "tests": ["full"]
        },
        "cmake-asan-gcc-sslv3": {
            "config": {"set": ["MBEDTLS_SSL_PROTO_SSL3"]},
            "build": "cmake",
            "environment": {"MAKE": "make", "CC": "gcc", "CMAKE_BUILD_TYPE": "ASan"},
            "tests": ["sslv3"]
        },
        "cmake-asan-gcc-no-renegotiation": {
            "config": {"unset": ["MBEDTLS_SSL_RENEGOTIATION"]},
            "build": "cmake",
            "environment": {"MAKE": "make", "CC": "gcc", "CMAKE_BUILD_TYPE": "ASan"},
            "tests": ["make test", "./programs/test/selftest", "SEED=1 ./tests/ssl-opt.sh"]
        },
        "cmake-asan-gcc-no-max-fragment-len": {
            "config": {"unset": ["MBEDTLS_SSL_MAX_FRAGMENT_LENGTH"]},
            "build": "cmake",
            "environment": {"MAKE": "make", "CC": "gcc", "CMAKE_BUILD_TYPE": "ASan"},
            "tests": ["./tests/ssl-opt.sh -f \"Max fragment length\""]
        },
        "cmake-asan-gcc-test-null-entropy": {
            "config": {
                "set": ["MBEDTLS_TEST_NULL_ENTROPY", "MBEDTLS_NO_DEFAULT_ENTROPY_SOURCES", "MBEDTLS_ENTROPY_C"],
                "unset": ["MBEDTLS_ENTROPY_NV_SEED", "MBEDTLS_ENTROPY_HARDWARE_ALT", "MBEDTLS_HAVEGE_C"]
            },
            "build": "cmake",
            "environment": {"MAKE": "make", "CC": "gcc", "UNSAFE_BUILD": "ON",
                "CFLAGS": "-fsanitize=address -fno-common -O3"},
            "tests": ["ctest -vv"]
        },
        "cmake-asan-rsa-no-crt": {
            "config": {"set": ["MBEDTLS_RSA_NO_CRT"]},
            "build": "cmake",
            "environment": {"MAKE": "make", "CC": "gcc", "CMAKE_BUILD_TYPE": "ASan"},
            "tests": ["make test", "./programs/test/selftest"]
        },
        "cmake-memsan": {
            "config": {"unset": ["MBEDTLS_AESNI_C"]},
            "build": "cmake",
            "environment": {"MAKE": "make", "CC": "clang", "CMAKE_BUILD_TYPE": "MemSan"},
            "tests": ["make test", "./programs/test/selftest", "SEED=1 ./tests/ssl-opt.sh", "SEED=1 tests/compat.sh"]
        },
        "cmake-release": {
            "build": "cmake",
            "environment": {"MAKE": "make", "CC": "clang", "CMAKE_BUILD_TYPE": "Release"},
            "tests": ["make memcheck", "./tests/ssl-opt.sh --memcheck", "SEED=1 tests/compat.sh --memcheck"]
        },
        "cmake-clang-full-config": {
            "config": {"config": "full", "unset": ["MBEDTLS_MEMORY_BACKTRACE"]},
            "build": "cmake",
            "environment": {"MAKE": "make", "CC": "clang", "CMAKE_BUILD_TYPE": "Check"},
            "tests": [
                "make test",
                "./programs/test/selftest",
                "SEED=1 ./tests/ssl-opt.sh",
                "SEED=1 OPENSSL_CMD='$OPENSSL_LEGACY' GNUTLS_CLI='$GNUTLS_LEGACY_CLI' GNUTLS_SERV='$GNUTLS_LEGACY_SERV' tests/compat.sh -e '3DES|DES-CBC3' -f 'NULL|DES|RC4|ARCFOUR'"
            ]
        },
        "cmake-out-of-src": {
            "build": "cmake",
            "environment": {"MAKE": "make", "CC": "gcc", "CMAKE_BUILD_DIR": "build"}
        },
        "curves": {
            "script": "./tests/scripts/curves.pl"
        },
        "keyexchanges": {
            "script": "./tests/scripts/key-exchanges.pl"
        },
        "gmake-clang": {
            "build": "make",
            "environment": {"MAKE": "gmake", "CC": "clang"},
            "tests": ["make test", "./programs/test/selftest"]
        },
        "cmake-clang": {
            "build": "cmake",
            "environment": {"MAKE": "make", "CC": "clang", "CMAKE_BUILD_TYPE": "Check"},
            "tests": ["make test", "./programs/test/selftest"]
        },
        "mingw-make": {
            "build": "mingw-make",
            "tests": ["make test", "./programs/test/selftest"]
        },
        "msvc12-32": {
            "build": "msvc12-32"
        },
        "msvc12-64": {
            "build": "msvc12-64"
        },
        "all.sh": {
            "script": "./tests/scripts/all.sh"
        },
        "print-environment": {
            "script": "./scripts/output_env.sh"
        },
        "check-recursion": {
            "script": "./tests/scripts/recursion.pl library/*.c"
        },
        "check-generated-files": {
            "script": "./tests/scripts/check-generated-files.sh"
        },
        "check-doxy-blocks": {
            "script": "./tests/scripts/check-doxy-blocks.pl"
        },
        "check-names": {
            "script": "./tests/scripts/check-names.sh"
        },
        "check-doxygen": {
            "script": "./tests/scripts/doxygen.sh"
        },
        "basic-build-test": {
            "script": "./tests/scripts/basic-build-test.sh"
        }
    },
    "test-scripts": {
        "full": [
            "ctest -vv",
            "./programs/test/selftest",
            "openssl version",
            "gnutls-serv -v ",
            "SEED=1 ./tests/compat.sh",
            "SEED=1 ./tests/ssl-opt.sh",
            "SEED=1 ./tests/scripts/test-ref-configs.pl"],
        "sslv3": [
            "make test",
            "SEED=1 ./tests/compat.sh -m 'tls1 tls1_1 tls1_2 dtls1 dtls1_2'",
            "SEED=1 OPENSSL_CMD=\"$OPENSSL_LEGACY\" tests/compat.sh -m 'ssl3'",
            "SEED=1 ./tests/ssl-opt.sh"
        ]
    },
    "campaigns": {
        "linux-tests1": ["make-gcc", "cmake", "cmake-full", "cmake-asan"],
        "linux-tests2": ["gmake-clang", "cmake-clang"],
        "windows-tests": ["mingw-make", "msvc12-32", "msvc12-64"],
        "all-tests": ["print-environment", "cmake-asan-gcc",
                      "cmake-clang-full-config", "cmake-asan-gcc-sslv3",
                      "cmake-asan-gcc-no-renegotiation", "curves",
                      "keyexchanges", "unix-make", "make-full-config",
                      "make-no-std-func-nv-seed", "make-no-srv", "make-no-client",
                      "make-no-net-entropy", "cmake-asan-gcc-no-max-fragment-len",
                      "cmake-asan-gcc-test-null-entropy", "make-shared",
                      "make-i386-on-x64", "make-ilp32-on-x64",
                      "make-32bit-bignum-limbs", "make-gcc-arm",
                      "make-gcc-arm-no-udbl", "make-arm5", "make-arm6-v7-a",
                      "make-arm6-v7-m", "make-arm6-v8.2-a",
                      "make-arm6-v8.2-a-64bit", "make-arm6-v8-m.main",
                      "make-allow-sha1-certs", "cmake-asan-rsa-no-crt",
                      "cross-build-windows", "cross-build-tests-windows",
                      "cross-build-dll", "cross-build-tests-dll",
                      "cmake-memsan", "cmake-release", "cmake-out-of-src",
                      "check-recursion", "check-generated-files",
                      "check-doxy-blocks", "check-names", "check-doxygen"],
        "all.sh": ["all.sh"],
        "basic-build-test": ["basic-build-test"],
    },
    "jobs": {
        "commit-tests": [{
            "platforms": ["debian-i386", "debian-x64"],
            "campaigns": ["linux-tests1"]
        }, {
            "platforms": ["freebsd"],
            "campaigns": ["linux-tests2"]
        }, {
            "platforms": ["windows-tls"],
            "campaigns": ["windows-tests"]
        }],
        "release-tests": [{
            "platforms": ["ubuntu-16.04-x64"],
            "campaigns": ["all-tests", "basic-build-test"]
        }],
        "nightly": [{
            "platforms": ["debian-i386", "debian-x64"],
            "campaigns": ["linux-tests1"]
        }, {
            "platforms": ["freebsd"],
            "campaigns": ["linux-tests2"]
        }, {
            "platforms": ["windows-tls"],
            "campaigns": ["windows-tests"]
        }, {
            "platforms": ["ubuntu-16.04-x64"],
            "campaigns": ["all-tests"]
        }]
    }
}

