# Defining builds and tests for CI and local testing
Mbed TLS has a comprehensive set tests containing unit tests, system tests and various scripts. In CI these tests are executed on different platforms, toolchains and build configurations. This large scale of tests and execution variations makes it difficult to create CI jobs. Especially when CI systems are unstable and we often tend to port the jobs to different systems. In order to solve these issues this document describes a CI agnostic data format for defining jobs, campaigns and builds that we execute in CI or locally on development machines. This data format is intended to serve following objectives:
- Separating CI scripts and Mbed TLS test scripts
- Ease of porting CI jobs to different CI systems
- Data driven CI jobs for consistent testing accross CI systems and development machines.
- Modular data for ease of creating different jobs
- Consistent execution of CI tests on develoopment machines for 
