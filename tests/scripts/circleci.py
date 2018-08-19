#!/usr/bin/env python

import sys
import yaml
import json
from build_info_parser import BuildInfo

circleci_platforms = {
    "ubuntu-16.04-x64" : {
        "image": "armmbed/mbedtls-ubuntu-16.04:0.0.1",
        "has" : ['linux']
    },
    "debian-i386" : {
        "image": "armmbed/mbedtls-debian-9-i386:0.0.1",
        "has" : ['linux']
    },
    "debian-x64" : {
        "image": "armmbed/mbedtls-debian-9-x64:0.0.1",
        "has" : ['linux']
    }
}

circleci_branches = {
    "nightly": ["development"],
    "release-tests": ["release-test"],
    "commit-tests": ["/^pull\/.*$/"],
}

def generate_jobs():
    jobs = dict()
    workflows = dict()
    build_info = BuildInfo()
    for job_name in build_info.get_jobs():
        workflow = dict()
        workflow_jobs = list()
        # Add 'scm' job

        for platform, build_name in build_info.get_builds_in_job(job_name):
            circleci_job_name = "%s-%s" % (build_name, platform)

            # Filter tests
            build_data = build_info.get_build(build_name)
            circleci_platform_info = circleci_platforms.get(platform, None)
            if not circleci_platform_info:
                print("Skipping job %s as image missing for platform '%s'"
                    % (circleci_job_name, platform))
                continue
            docker_image = circleci_platform_info['image']
            capabilities = circleci_platform_info.get('has', [])
            requirements = build_data['requirements']
            if requirements:
                platform_is_suitable = True
                for requirement in requirements:
                    if requirement not in capabilities:
                        platform_is_suitable = False
                        print("Skipping job %s as requirement '%s' is missing"
                        % (circleci_job_name, requirement))
                        break
                if not platform_is_suitable:
                    continue

            #print "%s on %s" % (build_name, platform)
            job_config = dict()
            job_config["working_directory"] = "~/"
            docker_images = list()
            docker_image = dict()
            docker_image["image"] = "armmbed/mbedtls-ubuntu-16.04:0.0.1"
            docker_images.append(docker_image)
            job_config["docker"] = docker_images

            # TODO filter jobs for unprovidable platforms!
            # platform to correct image mapping

            # Steps
            steps = list()
            # Persist data step
            attach_workspace_step = dict()
            attach_workspace_step_data = dict()
            attach_workspace_step_data["at"] = "~/"
            attach_workspace_step["attach_workspace"] = attach_workspace_step_data
            steps.append(attach_workspace_step)
            # Run step
            run_step = dict()
            run_step_data = dict()
            run_step_data["name"] = "check files"
            run_step_data["command"] = "ls -ltr; ls -ltr mbedtls"
            run_step["run"] = run_step_data
            steps.append(run_step)

            run_step = dict()
            run_step_data = dict()
            run_step_data["name"] = build_name
            run_step_data["command"] = "cd mbedtls; ./tests/scripts/builder.py build -r %s" % build_name
            run_step["run"] = run_step_data
            steps.append(run_step)
            job_config["steps"] = steps
            jobs[circleci_job_name] = job_config

            # Worflows
            workflow_job = dict();
            workflow_job[circleci_job_name] = { "requires": ["scm"] }
            if job_name in circleci_branches:
                workflow_job[circleci_job_name]["filters"] = {
                    'branches':
                    {
                        'only': circleci_branches[job_name]
                    }
                }
            workflow_jobs.append(workflow_job)


        if workflow_jobs:
            if job_name in circleci_branches:
                scm_job = {"scm": {"filters": {
                    "branches": {
                        "only": circleci_branches[job_name]
                    }
                } } }
            else:
                scm_job = "scm"
            workflow['jobs'] = [scm_job] + workflow_jobs
            workflows[job_name] = workflow

    return jobs, workflows



def update_circleci_yaml():
    config = None
    with open(".circleci/config.yml", "r") as f:
        config = yaml.load(f)
    # Keep job 'scm' and remove rest
    jobs, workflows = generate_jobs()
    scm = config['jobs']['scm']
    config['jobs'] = {'scm': scm}
    config['jobs'].update(jobs)
    config['workflows'] = {'version': config['workflows']['version']}
    config['workflows'].update(workflows)
    with open(".circleci/config.yml", "w") as f:
        yaml.dump(config, f, indent=2)


def dump_json():
    with open(".circleci/config.yml", "r") as f:
        config = yaml.load(f)
        print json.dumps(config, indent=4)


if __name__=="__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-j', '--dump-json']:
            dump_json()
        else:
            print("Unknown argument %s" % sys.argv[1])
    else:
        update_circleci_yaml()
