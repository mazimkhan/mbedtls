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
check_env TEST_NAME MBEDTLS_ROOT

cd ${MBEDTLS_ROOT}

if [ "$TEST_NAME" = "make" ]; then
    check_env CC MAKE
    ${MAKE} clean
    ${MAKE}
    ${MAKE} check
    ./programs/test/selftest

elif [ "$TEST_NAME" = "cmake" ]; then
    check_env CC MAKE
    cmake -D CMAKE_BUILD_TYPE:String=Check .
    ${MAKE} clean
    ${MAKE}
    ${MAKE} test
    ./programs/test/selftest

elif [ "$TEST_NAME" = "cmake-full" ]; then
    check_env CC MAKE
    cmake -D CMAKE_BUILD_TYPE:String=Check .
    ${MAKE} clean
    ${MAKE}
    ${MAKE} test
    ./programs/test/selftest
    openssl version
    gnutls-serv -v
    #export PATH=/usr/local/openssl-1.0.2g/bin:/usr/local/gnutls-3.4.10/bin:$PATH
    export SEED=1
    ./tests/compat.sh
    ./tests/ssl-opt.sh
    ./tests/scripts/test-ref-configs.pl

elif [ "$TEST_NAME" = "cmake-asan" ]; then
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
    ${MAKE} test
    ./programs/test/selftest
    #export PATH=/usr/local/openssl-1.0.2g/bin:/usr/local/gnutls-3.4.10/bin:$PATH
    export SEED=1
    ./tests/compat.sh
    ./tests/ssl-opt.sh
    ./tests/scripts/test-ref-configs.pl

elif [ "$TEST_NAME" = "all.sh" ]; then

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
    echo "Error: Unknown test \"$TEST_NAME\"!"
    exit 1
fi

