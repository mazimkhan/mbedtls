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


## Getting started
