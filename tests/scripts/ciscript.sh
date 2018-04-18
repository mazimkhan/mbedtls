#! /usr/bin/env sh

# ciscript.sh
#
# This file is part of mbed TLS (https://tls.mbed.org)
#
# Copyright (c) 2018, ARM Limited, All Rights Reserved



################################################################
#### Documentation
################################################################

# Purpose
# -------
#
# To build and test with specific tools, configuration, toolchain and
# set of tests.
#
# Interface
# ---------------------
# This script requires environment variables to identify the config,
# build type and tests. These are:
#   1. MBEDTLS_ROOT     - (mandatory) Toplevel directory.
#   2. CONFIG           - (optional) Argument for config.pl.
#   3. BUILD            - (mutually exclusive with SCRIPT) Build type.
#   4. SCRIPT           - (mutually exclusive with BUILD) Script to run.
#   5. RUN_BASIC_TEST   - (optional) Basic tests.
#   6. RUN_FULL_TEST    - (optional) Full tests = basic + SSL + config.
#
# All the environment variables must be supplied via cienv.sh file that
# this script sources at the start.
#
# There are other environment variables required based on the build and
# tests selected. These are checked under each build type using function
# check_env().
#
# Tools required
# ---------------------
# This script assumes the presence of the tools required by the
# scripts it runs. In addition it requires following tools:
#   1. perl - for running config.pl
#   2. make, cmake - build tools
#   3. gcc, clang - compilers
#   4. git
#
# Notes for users
# ---------------
#
# Warning: this script is destructive. The specified build mode and
# configuration can and will arbitrarily change the current CMake
# configuration. After running this script, the CMake cache will
# be lost and CMake will no longer be initialised.
#
# Notes for maintainers
# ---------------------
#
# This script dispatches tests in following order:
#   1. Change to specified configuration. (Optional)
#   2. Run specified build step or script. (Mandatory)
#   3. Run specified tests. (Optional)
#
# Tests are specified with following environment variables:
#   1. RUN_BASIC_TEST=1
#       * Execute CTest tests
#       * Execute ./programs/test/selftest
#   2. RUN_FULL_TEST=1
#       * Execute basic tests defined above
#       * Execute SSL tests
#       * Execute config tests
#

set -ex

if [ ! -x cienv.sh ]; then
    echo "Error: Environment file cenv.sh does not exists or it is not executable!"
    exit 1
fi

check_env(){
    for var in "$@"
    do
        eval value=\$$var
        if [ -z "${value}" ]; then
            echo "Error: Test $BUILD: Required env var $var not set!"
            exit 1
        fi
    done
}

msg()
{
    echo ""
    echo "******************************************************************"
    echo "* $1 "
    printf "* "; date
    echo "******************************************************************"
    current_section=$1
}


. ./cienv.sh
check_env TEST_NAME MBEDTLS_ROOT

cd ${MBEDTLS_ROOT}

################################################################
#### Change config if specified
################################################################
if [ "X${CONFIG:-X}" != XX ]; then
    if [ "${CONFIG}" = "sslv3" ]; then
        scripts/config.pl set MBEDTLS_SSL_PROTO_SSL3
    elif [ "${CONFIG}" = "no_ssl_renegotiation" ]; then
        scripts/config.pl unset MBEDTLS_SSL_RENEGOTIATION
    elif [ "${CONFIG}" = "full-config-no-mem-backtrace" ]; then
        scripts/config.pl full
        scripts/config.pl unset MBEDTLS_MEMORY_BACKTRACE
    elif [ "${CONFIG}" = "full-config-no-std-func-nv-seed" ]; then
        scripts/config.pl full
        scripts/config.pl set MBEDTLS_PLATFORM_NO_STD_FUNCTIONS
        scripts/config.pl unset MBEDTLS_ENTROPY_NV_SEED
    elif [ "${CONFIG}" = "full-config-no-srv" ]; then
        scripts/config.pl full
        scripts/config.pl set MBEDTLS_SSL_SRV_C
    elif [ "${CONFIG}" = "full-config-no-cli" ]; then
        scripts/config.pl full
        scripts/config.pl set MBEDTLS_SSL_CLI_C
    elif [ "${CONFIG}" = "full-config-no-net-entropy" ]; then
        scripts/config.pl full
        scripts/config.pl unset MBEDTLS_NET_C # getaddrinfo() undeclared, etc.
        scripts/config.pl set MBEDTLS_NO_PLATFORM_ENTROPY # uses syscall() on GNU/Linux
    elif [ "${CONFIG}" = "no-max-fragment-len" ]; then
        scripts/config.pl unset MBEDTLS_SSL_MAX_FRAGMENT_LENGTH
    elif [ "${CONFIG}" = "test-null-entropy" ]; then
        scripts/config.pl set MBEDTLS_TEST_NULL_ENTROPY
        scripts/config.pl set MBEDTLS_NO_DEFAULT_ENTROPY_SOURCES
        scripts/config.pl set MBEDTLS_ENTROPY_C
        scripts/config.pl unset MBEDTLS_ENTROPY_NV_SEED
        scripts/config.pl unset MBEDTLS_ENTROPY_HARDWARE_ALT
        scripts/config.pl unset MBEDTLS_HAVEGE_C

    elif [ "${CONFIG}" = "bignum-limbs" ]; then
        scripts/config.pl unset MBEDTLS_HAVE_ASM
        scripts/config.pl unset MBEDTLS_AESNI_C
        scripts/config.pl unset MBEDTLS_PADLOCK_C

    elif [ "${CONFIG}" = "baremetal" ]; then
        scripts/config.pl full
        scripts/config.pl unset MBEDTLS_NET_C
        scripts/config.pl unset MBEDTLS_TIMING_C
        scripts/config.pl unset MBEDTLS_FS_IO
        scripts/config.pl unset MBEDTLS_ENTROPY_NV_SEED
        scripts/config.pl set MBEDTLS_NO_PLATFORM_ENTROPY
        # following things are not in the default config
        scripts/config.pl unset MBEDTLS_HAVEGE_C # depends on timing.c
        scripts/config.pl unset MBEDTLS_THREADING_PTHREAD
        scripts/config.pl unset MBEDTLS_THREADING_C
        scripts/config.pl unset MBEDTLS_MEMORY_BACKTRACE # execinfo.h
        scripts/config.pl unset MBEDTLS_MEMORY_BUFFER_ALLOC_C # calls exit

    elif [ "${CONFIG}" = "baremetal-no-udbl" ]; then
        scripts/config.pl full
        scripts/config.pl unset MBEDTLS_NET_C
        scripts/config.pl unset MBEDTLS_TIMING_C
        scripts/config.pl unset MBEDTLS_FS_IO
        scripts/config.pl unset MBEDTLS_ENTROPY_NV_SEED
        scripts/config.pl set MBEDTLS_NO_PLATFORM_ENTROPY
        # following things are not in the default config
        scripts/config.pl unset MBEDTLS_HAVEGE_C # depends on timing.c
        scripts/config.pl unset MBEDTLS_THREADING_PTHREAD
        scripts/config.pl unset MBEDTLS_THREADING_C
        scripts/config.pl unset MBEDTLS_MEMORY_BACKTRACE # execinfo.h
        scripts/config.pl unset MBEDTLS_MEMORY_BUFFER_ALLOC_C # calls exit
        scripts/config.pl set MBEDTLS_NO_UDBL_DIVISION

    elif [ "${CONFIG}" = "baremetal-for-arm" ]; then
        scripts/config.pl full
        scripts/config.pl unset MBEDTLS_NET_C
        scripts/config.pl unset MBEDTLS_TIMING_C
        scripts/config.pl unset MBEDTLS_FS_IO
        scripts/config.pl unset MBEDTLS_ENTROPY_NV_SEED
        scripts/config.pl unset MBEDTLS_HAVE_TIME
        scripts/config.pl unset MBEDTLS_HAVE_TIME_DATE
        scripts/config.pl set MBEDTLS_NO_PLATFORM_ENTROPY
        # following things are not in the default config
        scripts/config.pl unset MBEDTLS_DEPRECATED_WARNING
        scripts/config.pl unset MBEDTLS_HAVEGE_C # depends on timing.c
        scripts/config.pl unset MBEDTLS_THREADING_PTHREAD
        scripts/config.pl unset MBEDTLS_THREADING_C
        scripts/config.pl unset MBEDTLS_MEMORY_BACKTRACE # execinfo.h
        scripts/config.pl unset MBEDTLS_MEMORY_BUFFER_ALLOC_C # calls exit
        scripts/config.pl unset MBEDTLS_PLATFORM_TIME_ALT # depends on MBEDTLS_HAVE_TIME

    elif [ "${CONFIG}" = "full-config-no-platform" ]; then
        scripts/config.pl full
        scripts/config.pl unset MBEDTLS_PLATFORM_C
        scripts/config.pl unset MBEDTLS_NET_C
        scripts/config.pl unset MBEDTLS_PLATFORM_MEMORY
        scripts/config.pl unset MBEDTLS_PLATFORM_PRINTF_ALT
        scripts/config.pl unset MBEDTLS_PLATFORM_FPRINTF_ALT
        scripts/config.pl unset MBEDTLS_PLATFORM_SNPRINTF_ALT
        scripts/config.pl unset MBEDTLS_PLATFORM_TIME_ALT
        scripts/config.pl unset MBEDTLS_PLATFORM_EXIT_ALT
        scripts/config.pl unset MBEDTLS_ENTROPY_NV_SEED
        scripts/config.pl unset MBEDTLS_MEMORY_BUFFER_ALLOC_C
        scripts/config.pl unset MBEDTLS_FS_IO
    elif [ "${CONFIG}" = "allow-sha1-in-certs" ]; then
        scripts/config.pl set MBEDTLS_TLS_DEFAULT_ALLOW_SHA1_IN_CERTIFICATES
    elif [ "${CONFIG}" = "rsa-no-cert" ]; then
        scripts/config.pl set MBEDTLS_RSA_NO_CRT
    elif [ "${CONFIG}" = "memsan" ]; then
        scripts/config.pl unset MBEDTLS_AESNI_C
    else
        scripts/config.pl ${CONFIG}
    fi
fi

################################################################
#### Perform build step
################################################################

if [ "X${BUILD:-X}" != XX ]; then
    if [ "$BUILD" = "make" ]; then
        check_env CC MAKE
        ${MAKE} clean
        ${MAKE} ${MAKE_TARGET}

    elif [ "$BUILD" = "cmake" ]; then
        check_env CC MAKE

        # Workaround for deprecated option fno-sanitize-recover
        set +e
        if [ "$CMAKE_BUILD_TYPE" = "ASan" ]; then
            grep "fno-sanitize-recover=undefined,integer" CMakeLists.txt
            if [ $? -ne 0 ]
            then
                sed -i s/"fno-sanitize-recover"/"fno-sanitize-recover=undefined,integer"/ CMakeLists.txt
            fi
        fi
        set -e

        CMAKE_BUILD_DIR=${CMAKE_BUILD_DIR:-$MBEDTLS_ROOT}
        mkdir -p $CMAKE_BUILD_DIR
        cd $CMAKE_BUILD_DIR

        cmake -D UNSAFE_BUILD=${UNSAFE_BUILD:-OFF} -D CMAKE_BUILD_TYPE:String=${CMAKE_BUILD_TYPE} $MBEDTLS_ROOT
        ${MAKE} clean
        ${MAKE}

    else
        echo "Error: Unknown build \"$BUILD\"!"
        exit 1
    fi
elif [ "X${SCRIPT:-X}" != XX ]; then
    $SCRIPT
else
    echo "Error: Neither BUILD nor SCRIPT defined!"
    exit 1
fi

################################################################
#### Perform tests
################################################################

if [ "$RUN_BASIC_TEST" = "1" ]; then
    if [ "X${CMAKE_BUILD_DIR:-X}" != XX ]; then
        cd $CMAKE_BUILD_DIR
    fi
    make test
    ./programs/test/selftest
fi

if [ "$RUN_CTEST_TEST" = "1" ]; then
    if [ "X${CMAKE_BUILD_DIR:-X}" != XX ]; then
        cd $CMAKE_BUILD_DIR
    fi
    ctest -vv
fi

if [ "$RUN_FULL_TEST" = "1" ]; then
    ctest -vv
    ./programs/test/selftest
    openssl version
    gnutls-serv -v
    export SEED=1
    ./tests/compat.sh
    ./tests/ssl-opt.sh
    ./tests/scripts/test-ref-configs.pl
fi

if [ "$RUN_SSL_OPT_TEST" = "1" ]; then
    export SEED=1
    ./tests/ssl-opt.sh
fi

if [ "$RUN_SSL_OPT_SHA1_TEST" = "1" ]; then
    ./tests/ssl-opt.sh -f "SHA-1"
fi

if [ "$RUN_SSL_OPT_MFL_TEST" = "1" ]; then
    ./tests/ssl-opt.sh -f "Max fragment length"
fi

if [ "$RUN_SSL_OPT_MEMCHECK_TEST" = "1" ]; then
    ./tests/ssl-opt.sh --memcheck
fi

if [ "$RUN_COMPAT_TEST" = "1" ]; then
    export SEED=1
    tests/compat.sh
fi

if [ "$RUN_COMPAT_MEMCHECK_TEST" = "1" ]; then
    export SEED=1
    tests/compat.sh --memcheck
fi

if [ "$RUN_COMPAT_RC4_DES_NULL_TEST" = "1" ]; then
    export SEED=1
    OPENSSL_CMD="$OPENSSL_LEGACY" GNUTLS_CLI="$GNUTLS_LEGACY_CLI" GNUTLS_SERV="$GNUTLS_LEGACY_SERV" tests/compat.sh -e '3DES\|DES-CBC3' -f 'NULL\|DES\|RC4\|ARCFOUR'
fi

if [ "$RUN_SSLV3_TEST" = "1" ]; then
    export SEED=1
    msg "test: SSLv3 - main suites (inc. selftests) (ASan build)" # ~ 50s
    make test

    msg "build: SSLv3 - compat.sh (ASan build)" # ~ 6 min
    ./tests/compat.sh -m 'tls1 tls1_1 tls1_2 dtls1 dtls1_2'
    OPENSSL_CMD="$OPENSSL_LEGACY" tests/compat.sh -m 'ssl3'

    msg "build: SSLv3 - ssl-opt.sh (ASan build)" # ~ 6 min
    ./tests/ssl-opt.sh
fi

if [ "$RUN_CURVES_TEST" = "1" ]; then
    tests/scripts/curves.pl
fi

if [ "$RUN_KEYEXCHANGES_TEST" = "1" ]; then
    tests/scripts/key-exchanges.pl
fi

if [ "$RUN_NO_64BIT_DIV_TEST" = "1" ]; then
    ! grep __aeabi_uldiv library/*.o
fi

if [ "$RUN_MEMCHECK_TEST" = "1" ]; then
    make memcheck
fi

if [ "$RUN_ARMC6_BUILD_TESTS_TEST" = "1" ]; then
    # ARM Compiler 6 - Target ARMv7-A
    armc6_build_test "--target=arm-arm-none-eabi -march=armv7-a"

    # ARM Compiler 6 - Target ARMv7-M
    armc6_build_test "--target=arm-arm-none-eabi -march=armv7-m"

    # ARM Compiler 6 - Target ARMv8-A - AArch32
    armc6_build_test "--target=arm-arm-none-eabi -march=armv8.2-a"

    # ARM Compiler 6 - Target ARMv8-M
    armc6_build_test "--target=arm-arm-none-eabi -march=armv8-m.main"

    # ARM Compiler 6 - Target ARMv8-A - AArch64
    armc6_build_test "--target=aarch64-arm-none-eabi -march=armv8.2-a"
fi

