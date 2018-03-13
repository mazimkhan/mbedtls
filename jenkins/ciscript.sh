#!/bin/sh

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
            echo "Error: Test $TEST_NAME: Required env var $var not set!"
            exit 1
        fi
    done
}

. ./cienv.sh
check_env TEST_NAME BUILD MBEDTLS_ROOT

cd ${MBEDTLS_ROOT}

################################################################
#### Perform build step
################################################################

if [ "$BUILD" = "make" ]; then
    check_env CC MAKE
    ${MAKE} clean
    ${MAKE}

elif [ "$BUILD" = "cmake" ]; then
    check_env CC MAKE
    cmake -D CMAKE_BUILD_TYPE:String=Check .
    ${MAKE} clean
    ${MAKE}

elif [ "$BUILD" = "cmake-asan" ]; then
    check_env CC MAKE

    set +e
    grep "fno-sanitize-recover=undefined,integer" CMakeLists.txt
    if [ $? -ne 0 ]
    then
        sed -i s/"fno-sanitize-recover"/"fno-sanitize-recover=undefined,integer"/ CMakeLists.txt
    fi
    set -e

    cmake -D CMAKE_BUILD_TYPE:String=ASan .
    ${MAKE}

elif [ "$BUILD" = "all.sh" ]; then

    if [ ! -d .git ]
    then
        git config --global user.email "you@example.com"
        git config --global user.name "Your Name"
        git init
        git add .
        git commit -m "CI code copy"
    fi
    ./tests/scripts/all.sh -r -k --no-yotta

else
    echo "Error: Unknown build \"$BUILD\"!"
    exit 1
fi

################################################################
#### Perform tests
################################################################

if [ "$RUN_BASIC_TEST" = "1" ]; then
    ctest -vv
    ./programs/test/selftest
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

