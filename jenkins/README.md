# CI instrumentation scripts
Scripts under this directory are used for deploying tests in the CI. These are kept with source for following reasons:

- Ease of defining and maintaining different CI jobs
- Reduce CI script complexity
- Revision specific testing
- Code reusability
- Quality control via reviews and possibly testing (future)

## CI Infrastructure and test entities relation
Following entity relation diagram shows the relation between different components involved in Mbed TLS testing:
```
              --------------- m        1 ----------
              | Slave label |------------|   CI   |
              ---------------            ----------
                      |1                      | 1
                      |                       |
                      |                       | m
                      |                  ----------
                      |                  |  Job   |
                      |                  ----------
                      |                       | m
                      |                       |
                      |1                      | m
                 ------------ m      m --------------- 1      m --------------------
                 | Platform |----------| Test script |----------| Test environment |
                 ------------          ---------------          --------------------

```
Terms used in above diagram
**CI** Continuous Integration infrastructure.
**Slave label** Label identifying a type of slave machines commissioned for running specific tests.
**Job** A test campaign run on a particular revision of source. Like PR, nightly, release testing.
**Test script** A test script or bunch of commands. It executes a test on a particular platform and environment.
**Platform** Target platform. Like Ubuntu, Debian, FreeBSD etc.
**Test environment** Environment to chang a test script behaviour. Like environment ```CC=gcc``` selects compiler GCC.

Based on above entity relation CI jobs can be defined with the meta data in following json format:

```py
ci_jobs = {
   "commit_tests": {
       'make-gcc': {
           'script': 'make',
           'environment': {'MAKE': 'make', 'CC': 'gcc'},
           'platforms': ['debian-9-i386', 'debian-9-x64'],

       },
       'gmake-gcc': {
           'script': 'make',
           'environment': {'MAKE': 'gmake', 'CC': 'gcc'},
           'platforms': ['debian-9-i386', 'debian-9-x64'],
       },
       'cmake': {
           'script': 'cmake',
           'environment': {'MAKE': 'gmake', 'CC': 'gcc'},
           'platforms': ['debian-9-i386', 'debian-9-x64'],
       },
       'cmake-full':  {
           'script': 'cmake-full',
           'environment': {'MAKE': 'gmake', 'CC': 'gcc'},
           'platforms': ['debian-9-i386', 'debian-9-x64'],
       },
       'cmake-asan': {
           'script': 'cmake-asan',
           'environment': {'MAKE': 'gmake', 'CC': 'clang'},
           'platforms': ['debian-9-i386', 'debian-9-x64'],
       },
       'mingw-make': {
           'script': 'mingw-make',
           'platforms': ['windows'],
       },
       'msvc12-32': {
           'script': 'msvc12-32',
           'platforms': ['windows'],
       },
       'msvc12-64': {
           'script': 'msvc12-64',
           'platforms': ['windows'],
       }
   },
   "release_tests": {
        'all.sh': {
            'script': './tests/scripts/all.sh',
            'platforms': ['ubuntu-16.04-x64']
        }
    }
}

```

Above, root element ```ci_jobs``` contains a collection of jobs in the form of dictionary elements. Job ```commit_tests``` further contains all the tests that need to be run as part of it. These tests may run in parallel depending on the CI implementation. Parallelization is out of scope of this solution.

Since the job and the test script have many to many relation. Commands of the test script are not defined here. They are referred by a name in this meta data. They are defined elsewhere and explained later.
