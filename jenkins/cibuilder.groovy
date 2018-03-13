
platform_to_docker_label_map = [
    "debian-i386" : "mbedtls && ubuntu-16.10-x64",
    "debian-x64" : "mbedtls && ubuntu-16.10-x64",
    "ubuntu-16.04-x64" : "mbedtls && ubuntu-16.10-x64"
]

windows_labels = [
    "windows-tls"
]

def create_subjob( test_name, platform, src_stash_name ) {
    def docker_lbl = platform_to_docker_label_map[platform]
    if( docker_lbl ) {
        return {
            node( docker_lbl ) {
                timestamps {
                    deleteDir()
                    unstash src_stash_name
                    sh """
./jenkins/cibuilder.py -e ${test_name}
echo \"MBEDTLS_ROOT=.\" >> cienv.sh
docker run --rm -u \$(id -u):\$(id -g) --entrypoint /var/lib/build/jenkins/ciscript.sh -w /var/lib/build -v `pwd`:/var/lib/build -v /home/ubuntu/.ssh:/home/mbedjenkins/.ssh ${platform}
"""
                }
            }
        }
    } else {
        return {
            node( platform ) {
                timestamps {
                    deleteDir()
                    unstash src_stash_name
                    if( platform in windows_labels ){
                        bat """
python jenkins\\cibuilder.py -e ${test_name}
echo set MBEDTLS_ROOT=. >> cienv.bat
.\\jenkins\\ciscript.bat
"""
                    } else {
                        if( platform == "freebsd" ){
                            sh """
/usr/local/bin/python2.7 ./jenkins/cibuilder.py -e ${test_name}
echo \"export PYTHON=/usr/local/bin/python2.7\" >> cienv.sh
"""
                        } else {
                            sh """
./jenkins/cibuilder.py -e ${test_name}
"""
                        }
                        sh """
echo \"MBEDTLS_ROOT=.\" >> cienv.sh
./jenkins/ciscript.sh
"""
                    }
                }
            }
        }
    }
}

def create_parallel_jobs( campaign, src_stash_name ){
    sh """
./jenkins/cibuilder.py -c ${campaign} -o tests.txt
    """
    def test_jobs = [:]
    tests = readFile 'tests.txt'
    def test_list = tests.split( '\n' )
    /* Use C style loop as it is serializable and allow calling this function
     * after loading this script from Jenkins groovy. */
    for( int i = 0; i < test_list.size(); i++ ) {
        def test = test_list[i]
        def test_details = test.split( '\\|' )
        def test_name = test_details[0]
        def platform = test_details[1]
        def job = create_subjob( test_name, platform, src_stash_name )
        if( job ){
            test_jobs[test_name] = job
        } else {
            echo "Failed to create job for ${test_name} ${platform}"
        }
    }
    return test_jobs
}

return this
