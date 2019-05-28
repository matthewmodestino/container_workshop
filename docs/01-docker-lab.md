# Docker Lab
Docker is a widely adopted container runtime engine that will very likely be part the stack that you encounter in container environments. Understanding the Docker layer is a great base for jumping into the world of container orchestrators like Kubernetes and Openshift. 

The Purpose of this lab is to familiarize you with the data sources and integrations that Docker Enterprise, or Docker-esque environments (ECS, Fargate) will use. 

Here are the docs for some helpful commands that we will be using. 

```
docker version
#https://docs.docker.com/engine/reference/commandline/version/

docker plugin ls
#https://docs.docker.com/engine/reference/commandline/plugin/

docker inspect
#https://docs.docker.com/engine/reference/commandline/inspect/

docker logs
#https://docs.docker.com/engine/reference/commandline/logs/

docker-compose
#https://docs.docker.com/compose/reference/overview/
```

> BONUS: Check out CRI-O, a popular docker alternative that companies like IBM/Red Hat Openshift are adopting. https://cri-o.io/ 

## Deploy Splunk Enterprise

We will be using docker-compose commands to deploy a standalone Splunk server using provided yaml files. See the docker-splunk repo test_scenarios folder for more examples. 

To learn more about docker-compose, READ ME! https://docs.docker.com/compose/compose-file/

This Splunk deploy will receive data from various integrations we review in the following labs.

Navigate to `splunk_docker` folder

```
docker-compose -f 1so_hec.yaml up -d
```

Tail the splunk container’s logs. Splunk docker images leverage the splunk-ansible project as our entrypoint. Once ansible play recap is completed, your splunk instance is ready. 

Find your container id

```
docker ps -a
CONTAINER ID        IMAGE                  COMMAND                  CREATED             STATUS                             PORTS                                                                                                                      NAMES
dab0461d7b46        splunk/splunk:latest   "/sbin/entrypoint.sh…"   32 seconds ago      Up 30 seconds (health: starting)   4001/tcp, 8065/tcp, 8191/tcp, 9887/tcp, 9997/tcp, 0.0.0.0:9999->8000/tcp, 0.0.0.0:9088->8088/tcp, 0.0.0.0:9089->8089/tcp   so1
```


```
docker logs -f dab0461d7b46


PLAY RECAP *********************************************************************
localhost                  : ok=37   changed=7    unreachable=0    failed=0   

Tuesday 30 April 2019  14:40:37 +0000 (0:00:00.023)       0:00:38.643 ********* 
=============================================================================== 
splunk_common : Install Splunk (Linux) --------------------------------- 22.93s
splunk_common : Start Splunk via cli ------------------------------------ 5.34s
splunk_common : Enable the Splunk-to-Splunk port ------------------------ 1.92s
Gathering Facts --------------------------------------------------------- 1.45s
splunk_common : Hash the password --------------------------------------- 0.67s
splunk_common : Generate user-seed.conf --------------------------------- 0.46s
splunk_common : Test basic https endpoint ------------------------------- 0.40s
splunk_common : Check if we are in a docker ----------------------------- 0.40s
splunk_common : Create .ui_login ---------------------------------------- 0.38s
splunk_common : Remove installers --------------------------------------- 0.29s
splunk_common : Update Splunk directory owner --------------------------- 0.28s
splunk_common : Wait for port 8089 to become open ----------------------- 0.27s
splunk_common : Find manifests ------------------------------------------ 0.27s
splunk_common : Check for existing installation ------------------------- 0.26s
splunk_standalone : Check for required restarts ------------------------- 0.23s
splunk_common : Remove user-seed.conf ----------------------------------- 0.16s
splunk_common : Check for existing splunk secret ------------------------ 0.16s
Provision role ---------------------------------------------------------- 0.12s
splunk_common : include_tasks ------------------------------------------- 0.10s
splunk_common : include_tasks ------------------------------------------- 0.10s
===============================================================================

Ansible playbook complete, will begin streaming var/log/splunk/splunkd_stderr.log
```

### Test HEC

Let’s ensure the HEC configuration defined in the compose file allows us to send data to Splunk. 

```
curl -k https://localhost:9088/services/collector -H 'Authorization: Splunk 00000000-0000-0000-0000-000000000000' -d '{"sourcetype": "mysourcetype", "event":"Hello, World!"}'
```

We now have a functioning standalone Splunk environment. Now let’s fill it with data!

For more on docker-splunk images and support, or to learn about splunk-ansible, visit the projects on Github!

## Install Splunk Connect for Docker

The quickest and easiest way to demo docker logs to Splunk, is to try out the Splunk Connect for Docker. Not to be confused with the original Docker Logging Driver, This Logging Plugin uses Docker’s plugin framework and should be used in place of the original driver, if possible. (see system requirements in the github repo). This is a good solution if you want to ONLY collect docker logs. This solution does not collect metrics or non docker logs from a system. For that you would need a UF or Fluentd, or Outcold Solutions collectord.

https://hub.docker.com/plugins/splunk-connect-for-docker
https://github.com/splunk/docker-logging-plugin

```
docker plugin install splunk/docker-logging-plugin
```

### Configure the Logging Plugin
Once installed, the plugin is very easy to configure through the docker desktop UI. It even included json syntax checks. 

https://docs.docker.com/docker-for-mac/#daemon

Here are some configs you can paste into the advanced daemon screen on Docker Desktop. 

See all config options for Splunk Logging Plugin here: https://github.com/splunk/docker-logging-plugin/blob/release/2.0.1/README.md

### Try the default “inline” format

```
 "log-driver" : "4e534fbc6e71",
  "log-opts" : {
    "splunk-url" : "https://localhost:9088",
    "splunk-insecureskipverify" : "true",
    "splunk-token" : "00000000-0000-0000-0000-000000000000"
  }
```

### Try the Raw format

```
 "log-driver" : "4e534fbc6e71",
  "log-opts" : {
    "splunk-format" : "raw",
    "splunk-url" : "https://localhost:9088",
    "splunk-insecureskipverify" : "true",
    "splunk-token" : "00000000-0000-0000-0000-000000000000"
  }
```

### Deploy a sample app
To examine the formats mentioned above, you can deploy buttercupgo. 

Each time you change the Docker daemon settings and restart, or use docker restart command to restart the buttercupgo image, you should see logs in Splunk. 

```
docker-compose -f buttercupgo.yaml up -d
```
> HINT: visit localhost:3040 when buttercupgo is running if you need a break from all his docker talk already!! :)

> HINT HINT: buttercup go is instrumented with boomerang.js. and Logs2Metrics is a thing now! We will look to ingest the boomerang data directly into Splunk metrics in a future lab. 
Review

## Review 

#docker-community, #dockerizing-splunk #project-docker-plugin & #project-k8s


>What do you think of the various data formats?
>What will happen to sourcetypes you may have configured?
>What about multiline logging?

## Clean Up

```
docker-compose -f buttercupgo.yaml down

docker-compose -f 1so_hec.yaml down

docker volume prune

docker plugin disable 65d7fec7b834

docker plugin rm 65d7fec7b834

```


# BONUS LABS!

There are many ways to achieve results with Splunk. The following are alternate integration options to Splunk Connect for Docker that we have seen, internally and in the field. 

## splunk-fluent-hec
https://hub.docker.com/r/splunk/fluentd-hec

The topic of data formatting and multiline logging will be where the discussion moves once a customer gets running with Splunk Connect for Docker. The plugin does not support multiline logs (stacktraces, etc), so using Splunk’s fluentd-hec images looks like a good alternative, and aligns with Splunk Connect for Kubernetes, which we will cover in the next lab. 

I have included Fluentd Docker Images with a barebones PoC docker configuration that can address this, and provides opportunity for us to simplify the solutions we support in this space. 

```
docker-compose -f fluent_hec.yaml up -d
```

This would allow coverage of docker, k8s and openshift with a single logging image. 

More experimentation with this to come!

## Syslog Driver with syslog-ng & HEC

I have not ventured into this world, due to the fact that it would generally require customization of the container environment. Still, it should be investigated and compared for scale, reliability, features, against other options. The main detractor is that while syslog is a supported Docker driver, it breaks the `docker logs` and `kubectl logs` commands, which may or may not be a big deal for your environment/teams. 
Collectd for Docker Metrics
With Splunk making collectd a first class input for metrics (see write_splunk plugin that SAI uses), using collectd to collect metrics from docker nodes looks very promising.

I have used open-source plugins to PoC this, and it works very well. I would look for SAI to create an official plugin in the future.  

# Troubleshooting the Docker Labs

Check `docker logs -f <yourContainerID>` to ensure the ansible plays finish successfully. 

If your Splunk image has errors in the Ansible Play Recap, review the error and the associated splunk-ansible play. Also check the rendered configuration that the container dumps on startup for issues. Here is a working example:

```
$ docker logs -f 36cb6a7af601
ansible-playbook 2.7.10
  config file = /opt/ansible/ansible.cfg
  configured module search path = [u'/opt/ansible/library', u'/opt/ansible/apps/library', u'/opt/ansible/ansible_commands']
  ansible python module location = /usr/lib/python2.7/dist-packages/ansible
  executable location = /usr/bin/ansible-playbook
  python version = 2.7.13 (default, Sep 26 2018, 18:42:22) [GCC 6.3.0 20170516]
{
    "_meta": {
        "hostvars": {
            "localhost": {
                "ansible_connection": "local"
            }
        }
    }, 
    "all": {
        "children": [
            "ungrouped"
        ], 
        "hosts": [
            "localhost"
        ], 
        "vars": {
            "ansible_post_tasks": null, 
            "ansible_pre_tasks": null, 
            "ansible_ssh_user": "splunk", 
            "config": {
                "baked": "default.yml", 
                "defaults_dir": "/tmp/defaults", 
                "env": {
                    "headers": null, 
                    "var": "SPLUNK_DEFAULTS_URL", 
                    "verify": true
                }, 
                "host": {
                    "headers": null, 
                    "url": null, 
                    "verify": true
                }, 
                "max_delay": 60, 
                "max_retries": 3, 
                "max_timeout": 1200
            }, 
            "delay_num": 3, 
            "docker_version": "18.06.0", 
            "hide_password": false, 
            "retry_num": 50, 
            "shc_bootstrap_delay": 30, 
            "splunk": {
                "admin_user": "admin", 
                "allow_upgrade": true, 
                "app_paths": {
                    "default": "/opt/splunk/etc/apps", 
                    "deployment": "/opt/splunk/etc/deployment-apps", 
                    "httpinput": "/opt/splunk/etc/apps/splunk_httpinput", 
                    "idxc": "/opt/splunk/etc/master-apps", 
                    "shc": "/opt/splunk/etc/shcluster/apps"
                }, 
                "apps_location": [], 
                "build_location": "/tmp/splunk-7.2.6-c0bf0f679ce9-Linux-x86_64.tgz", 
                "build_remote_src": false, 
                "deployer_included": false, 
                "enable_service": false, 
                "exec": "/opt/splunk/bin/splunk", 
                "group": "splunk", 
                "hec_disabled": 0, 
                "hec_enableSSL": 1, 
                "hec_port": 8088, 
                "hec_token": "00000000-0000-0000-0000-000000000000", 
                "home": "/opt/splunk", 
                "http_enableSSL": 0, 
                "http_enableSSL_cert": null, 
                "http_enableSSL_privKey": null, 
                "http_enableSSL_privKey_password": null, 
                "http_port": 8000, 
                "idxc": {
                    "enable": false, 
                    "label": "idxc_label", 
                    "replication_factor": 3, 
                    "replication_port": 9887, 
                    "search_factor": 3, 
                    "secret": null
                }, 
                "ignore_license": false, 
                "indexer_cluster": false, 
                "license_download_dest": "/tmp/splunk.lic", 
                "license_master_included": false, 
                "license_uri": "splunk.lic", 
                "nfr_license": "/tmp/nfr_enterprise.lic", 
                "opt": "/opt", 
                "password": "**************", 
                "pid": "/opt/splunk/var/run/splunk/splunkd.pid", 
                "role": "splunk_standalone", 
                "s2s_enable": true, 
                "s2s_port": 9997, 
                "search_head_cluster": false, 
                "search_head_cluster_url": null, 
                "secret": null, 
                "shc": {
                    "enable": false, 
                    "label": "shc_label", 
                    "replication_factor": 3, 
                    "replication_port": 9887, 
                    "secret": null
                }, 
                "smartstore": null, 
                "svc_port": 8089, 
                "tar_dir": "splunk", 
                "user": "splunk", 
                "wildcard_license": false
            }, 
            "splunk_home_ownership_enforcement": true
        }
    }, 
    "ungrouped": {
        "hosts": []
    }
}

```

You can also use the docker inspect command to review your container settings. 

Troubleshooting tips on github! 
https://github.com/splunk/docker-splunk/blob/develop/docs/TROUBLESHOOTING.md

