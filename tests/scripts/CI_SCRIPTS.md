# CI scripts
This document describes the data driven framework for Mbed TLS CI. This is composed of:

- A **Data format** for defining the CI jobs in a CI system agnostic way.
- **Scripts** to introspect and execute CI jobs in a CI system. 

## Requirements
Purpose of this framework is to make it easy to define, deploy and maintain CI. It fulfills following requirements:
- Separate common CI test orchestration from CI system specific scripts (ex: Jenkins pipeline groovy or CircleCI yaml). For
  - reproducing the CI steps on development machines for testing and debugging, and
  - make it easily portable to the different CI systems.
- Implement CI test orchestration as easy to maintain Python scripts.
- Reuse common build and test steps.
- Version control CI scripts to allow revision specific testing and quality control via code review process.

## Gist
This section explains the setting up of CI data with the help of examples.

The CI data is loaded from a python file: `mbedtls/tests/scripts/build_info.py` in the form of Python objects. Example:
```py
data = {
  "builds": {
    ...
  },
  "campaigns": {
    ...
  },
  "jobs": {
    ...
  }
}
```
Add a build to the collection of `builds` as:
```py
data = {
  "builds": {
        "make-gcc": {
            "build": "make",
            "environment": {"MAKE": "make", "CC": "gcc"},
            "tests": ["make test", "./programs/test/selftest"]
        },
        ...
   }
   ...
}
```
Above, the term **build** is used, since the tests are preceded by a build step for a particular configuration and toolchain. The tests for a build are specified as a list of commands.

A group of builds create a **campaign**:
```py
data = {
  ...
  "campaigns": {
    "linux-tests1": ["make-gcc", "cmake", "cmake-full", "cmake-asan"],
    ...
  },
  ...
}
```

Finally, a CI job is specified as a collection of campaigns and corresponding target platforms.
```py
data = {
    ...

    "jobs": {
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
    },
   ...
}
```

For the detailed description of the format please see [Format Reference](#format-reference).

## Tools
CI data can be validated by running 
```py
mbedtls/tests/scripts/build_info_parser.py
```
`build_info_parser.py` is also imported by the other scripts to validate and parse the data out of `build_info.py`.

CI data can be introspected to create CI builds in a CI system with command:
```py
./tests/scripts/builder.py jobs -t <job name>

debian-i386|cmake
debian-i386|cmake-asan
debian-i386|cmake-full
...
```

A CI build can be an execution instance in the CI system that executes a build step and the associated tests.



## Format Reference
### Categorisation
