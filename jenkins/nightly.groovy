
node {
    deleteDir()
    checkout([$class: 'GitSCM', branches: [[name: BRANCH]],
        doGenerateSubmoduleConfigurations: false,
        extensions: [[$class: 'CloneOption', honorRefspec: true,
        noTags: true, reference: '', shallow: true]],
        submoduleCfg: [],
        userRemoteConfigs: [[credentialsId: "${env.GIT_CREDENTIALS_ID}",
        url: MBEDTLS_REPO]]])
    stash 'src'

    def Jenkinsfile = load "${rootDir}@script/Jenkinsfile"
    def branches = Jenkinsfile.create_parallel_jobs( "nightly" )

    parallel branches
}

