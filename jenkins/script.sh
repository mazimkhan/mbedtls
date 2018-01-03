!#/bin/sh

set -e
set -x
set -v

MAKE=gmake
CC=clang

set +e
grep "fno-sanitize-recover=undefined,integer" CMakeLists.txt
if [ $? -ne 0 ]; 
then 
    sed -i s/"fno-sanitize-recover"/"fno-sanitize-recover=undefined,integer"/ CMakeLists.txt; 
fi
set -e
cmake -D CMAKE_BUILD_TYPE:String=ASan .
make
make test
./programs/test/selftest
export PATH=/usr/local/openssl-1.0.2g/bin:/usr/local/gnutls-3.4.10/bin:$PATH
export SEED=1
./tests/compat.sh
./tests/ssl-opt.sh
./tests/scripts/test-ref-configs.pl
