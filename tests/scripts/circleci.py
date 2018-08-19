#!/usr/bin/env python

import yaml
import json
from build_info_parser import BuildInfo

circleci_platforms = {
    "ubuntu-16.04-x64" : {
        "image": "armmbed/mbedtls-ubuntu-16.04:0.0.1",
        "has" : ['linux']
    }
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
                print("Build %s has requirements %s" % (build_name,
                str(requirements)))
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
            workflow_job[circleci_job_name] = { "requires": ["scm"]}
            workflow_jobs.append(workflow_job)

        if workflow_jobs:
            workflow['jobs'] = ["scm"] + workflow_jobs
            workflows[job_name] = workflow

    return jobs, workflows



def update_circleci_yaml():
    config = None
    with open(".circleci/config.yml", "r") as f:
        config = yaml.load(f)
        #print json.dumps(y, indent=4)
    # Keep job 'scm' and remove rest
    jobs, workflows = generate_jobs()
    scm = config['jobs']['scm']
    config['jobs'] = {'scm': scm}
    config['jobs'].update(jobs)
    config['workflows'] = {'version': config['workflows']['version']}
    #print json.dumps(workflows, indent=4)
    config['workflows'].update(workflows)
    with open(".circleci/config.yml", "w") as f:
        yaml.dump(config, f, indent=2)
    #print json.dumps(config, indent=4)


if __name__=="__main__":
    update_circleci_yaml()
    #print_yml()
