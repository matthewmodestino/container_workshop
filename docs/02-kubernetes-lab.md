# Kubernetes Lab

## Configure Docker Desktop to run Kubernetes

One of the really handy things about using Docker Desktop is that it can also deploy Kubernetes! 

Let’s configure our Kubernetes environment. 

https://docs.docker.com/docker-for-mac/#kubernetes

Docker Desktop deploys the necessary Kubernetes infrastructure as Docker containers in a hyperkit vm. Docker takes care of wiring up all the glue that makes it work locally. 

If you want to take a closer look at the actual VM, run the following command, after enabling Kubernetes in Docker Desktop. 

```
screen ~/Library/Containers/com.docker.docker/Data/vms/0/tty

```

To exit the VM, run:

```
ctrl+A then K, then Y
```

## Create a Splunk Namespace
```
kubectl create ns splunk
```

## Deploy Splunk Standalone
The image used in this deployment has Splunk apps mounted in the /tmp directory and defined in the SPLUNK_APPS_URL environment variable. This is done to simplify the workshop. There are many ways to copy your config data into place, like pulling from splunkbase or from a web server. See advanced docs for more. 

From the splunk_k8s directory, run 

```
kubectl -n splunk apply -f standalone
```


## kubectl port-forward

Access the splunk instance using kubectl port-forward to verify it is running. 

## kubectl exec

Access the container and test HEC. 

Notice you are the ansible user. This user has sudo. Splunk runs as user splunk. 

```
curl -k https://standalone:8088/services/collector -H 'Authorization: Splunk 00000000-0000-0000-0000-000000000000' -d '{"sourcetype": "mysourcetype", "event":"Hello, World!"}'
```


## Install and Deploy Helm

Helm is a package manager for Kubernetes and makes deploying much easier than having to manage yaml manually. Splunk Connect for Kubernetes supports HELM. If your customer does not use helm, they can use our manifests as a guide and deploy manually, or use HELM’s template command locally. 

Install Helm locally on your laptop:

https://helm.sh/docs/using_helm/#installing-helm

from inside the helm folder deploy the tiller RBAC configuration

```
 kubectl -n splunk apply -f tiller-rbac-config.yaml
serviceaccount "tiller" created
clusterrolebinding.rbac.authorization.k8s.io "tiller" created
```

## Deploy Tiller to the cluster

```
helm init --service-account tiller --tiller-namespace splunk
```

> You can also review this deploy guide which covers similar topics that we are about to cover:
https://www.splunk.com/blog/2019/03/01/deploy-splunk-enterprise-on-kubernetes-splunk-connect-for-kubernetes-and-splunk-insights-for-containers-beta-part-3.html

Now that tiller is running, we can use our values.yaml file and deploy Splunk Connect for Kubernetes to send data about our Kubernetes environment to the Splunk instance we deployed in the previous steps

```
#global settings
global:
  logLevel: info 
  splunk:
    hec:
      protocol: https
      insecureSSL: false
      host: standalone
      token: 00000000-0000-0000-0000-000000000000

#local config for logging chart
splunk-kubernetes-logging:
  kubernetes:
    clusterName: docker-for-mac
  journalLogPath: /run/log/journal
  splunk:
    hec:
      indexName: cm_events 

#local config for objects chart      
splunk-kubernetes-objects:
  rbac:
    create: true
  serviceAccount:
    create: true
    name: splunk-kubernetes-objects
  kubernetes:
    clusterName: docker-for-mac
    insecureSSL: true
  objects:
    core:
      v1:
        - name: pods
          interval: 30s
        - name: namespaces
          interval: 30s
        - name: nodes
          interval: 30s
        - name: services
          interval: 30s
        - name: config_maps
          interval: 30s
        - name: persistent_volumes
          interval: 30s
        - name: service_accounts
          interval: 30s
        - name: persistent_volume_claims
          interval: 30s
        - name: resource_quotas
          interval: 30s
        - name: component_statuses
          interval: 30s
        - name: events
          mode: watch
    apps:
      v1:
        - name: deployments
          interval: 30s
        - name: daemon_sets
          interval: 30s
        - name: replica_sets
          interval: 30s
        - name: stateful_sets
          interval: 30s
  splunk:
    hec:
      indexName: cm_meta    
          
#local config for metrics chart
splunk-kubernetes-metrics:
  kubernetes:
    clusterName: docker-for-mac
    kubeletPort: 10250
    useRestClientSSL: true
    insecureSSL: true
  buffer:
    chunk_limit_records: 10000
  aggregatorBuffer:
    chunk_limit_records: 10000
  rbac:
    create: true
  serviceAccount:
    create: true
    name: splunk-kubernetes-metrics
  splunk:
    hec:
      indexName: cm_metrics
```

## Deploy Splunk Connect for Kubernetes

```
helm install --name sck-1.1.0 --tiller-namespace splunk --namespace splunk -f values.yaml https://github.com/splunk/splunk-connect-for-kubernetes/releases/download/1.1.0/splunk-connect-for-kubernetes-1.1.0.tgz
```

## Review Indexes and Sourcetypes

Now that Splunk Connect for Kubernetes is sending data in, let’s explore the indexes and sourcetypes. 

The sourcetypes are dynamically created based on rules set in fluentd, using our jq_transformer. 

## Review

Thoughts? As you can see, Splunk Connect for Kubernetes solves for the challenges admins and app teams are faced with in dealing with their data chaos. 



## Clean Up



## Troubleshooting

