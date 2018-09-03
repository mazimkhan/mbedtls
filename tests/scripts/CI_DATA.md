# Defining CI
This document describes the data driven framework for Mbed TLS CI. This is composed of:

- **Data format** for defining the CI jobs in a way that is agnostic to a particular CI system.
- **Tools** to introspect and execute CI jobs from a CI system. 

## Requirements
Purpose of this framework is to make it easy to define, deploy and maintain CI tests. Following requirements are considered in this framework:

#### Separate tests from the CI scripts
This framework separates Mbed TLS tests from the CI scripts for following benifits:
- Ease of development and maintenance. Tests can be defined in a CI agnostic way and included as a one liner in a CI job. No need to script them in CI specific scripting languages like: shell scripts, Python, groovy, yaml etc. No need to mix tests with CI specifics like resource management, parallel execution, version control etc. Hence, no complexity.
- Portability of CI jobs. Separation makes it easier to plug this framework into any CI system. Since, the CI systems often break and fail to execute certain tests properly or completely. This framework makes porting very easy. Also, parts of the test plan can be run in different CI systems.

#### Reproducibility of tests
Defining the tests as data and providing tools to execute them provides a consistent way of executing tests in the CI and on a development machine. Hence, it is easy to reproduce a test that is failing in the CI and debug it.

#### Reusability
The data format allows defining the tests and including them in different jobs. This reusability enables compact data definition. Also, some common tasks like setting environment, cleanup etc. is taken care by the tools.

#### Version control
This framework is part of Mbed TLS source, hence it is version controlled. It brings following benefits:
- Revision specific testing. Scripts can have specific steps for the same version of code and test scripts. As the steps or script options may differ in different revisions of the source. 
- As part of version control the CI tests' data and tools are become subject to code reviews and CI tests. Hence, improving test system quality.


## Gist
This section explains the setting up of CI data with the help of examples.

The CI data is loaded from a python file: `mbedtls/tests/scripts/build_info.py` with the data in the form of Python objects. Three mandatory attributes **builds, campaigns and jobs** are required:
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
Above term **build** is used, since tests are preceded by a build step with a particular configuration and toolchain. The tests for a build are specified as a list of commands.

A group of builds creates a **campaign**:
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

Next a CI job can be specified as a collection of campaigns with the target platforms.
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

For detailed description of the format please see **Format Reference**.

## Tools
CI data can be validated by running 
```py
mbedtls/tests/scripts/build_info_parser.py
```
`build_info_parser.py` can be executed to validate the data format. It is also imported by the other tools to validate and parse the data out of `build_info.py`.

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
