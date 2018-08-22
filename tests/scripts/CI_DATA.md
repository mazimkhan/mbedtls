# Defining CI
This document describes the data driven framework for Mbed TLS CI. This is composed of:

- **Data format** for defining the CI jobs in a way that is agnostic to a particular CI system.
- **Tools** to introspect and execute CI jobs from a CI system. 

## Requirements
Purpose of this framework is to make it easy to define, deploy and maintain CI tests. Following requirements are considered in this framework:

### Separate tests from the CI scripts
This framework separates Mbed TLS tests from the CI scripts for following benifits:
- Ease of development and maintenance. Tests can be defined in a CI agnostic way and included as a one liner in a CI job. No need to script them in CI specific scripting languages like: shell scripts, Python, groovy, yaml etc. No need to mix tests with CI specifics like resource management, parallel execution, version control etc.
- Portability of CI jobs. Separation makes it easier to plug this framework into any CI system. Since, the CI systems often break and fail to execute certain tests properly or completely. This framework makes porting very easy.

### Reproducibility of tests
Defining the tests as data and providing tools to execute them provides a consistent way of executing tests in the CI and on a development machine. Hence, it is easy to reproduce a test that is failing in the CI and debug it.

### Reusability
The data format allows defining the tests and including them in different jobs. This reusability enables compact data definition. Also, some common tasks like setting environment, cleanup etc. is taken care by the tools.

### Revision specific testing

### Version control

Mbed TLS has a comprehensive set tests containing unit tests, system tests and various scripts. In CI these tests are executed on different platforms, toolchains and build configurations. This large scale of tests and execution variations makes it difficult to create CI jobs. Especially when CI systems are unstable and we often tend to port the jobs to different systems. In order to solve these issues this document describes a CI agnostic data format for defining jobs, campaigns and builds that we execute in CI or locally on development machines. This data format is intended to serve following objectives:
- Separating CI scripts and Mbed TLS test scripts
- Ease of porting CI jobs to different CI systems
- Data driven CI jobs for consistent testing accross CI systems and development machines.
- Modular data for ease of creating different jobs
- Consistent execution of CI tests on develoopment machines for 
