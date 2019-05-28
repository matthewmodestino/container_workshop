# Openshift Lab

##Explore Openshift
If your customer is using Openshift, all the content we just covered for Open Soure Kubernetes still applies; we just put a little red hat on a few things. Openshift provides advanced security and permission controls, so we will deploy with additional configs to ensure we have the access and permissions we need. 

https://docs.okd.io/latest/architecture/index.html

Let’s explore. After Installing Minishift and the `oc` command on your laptop, log in as the Openshift admin

```
oc login -u system:admin
```

Let’s deploy a standalone instance of Splunk Enterprise to send data to. 

# Deploy Splunk

## Create a Splunk Project

Notice we clear the node selector label to ensure our daemonsets can run on master nodes. 

```
oc adm new-project splunk --node-selector=""
```

## Select the project

```
oc project splunk
```

At anytime, check what cluster and project you are working on:

```
oc status
```

## Create a service account called splunk

```
oc create sa splunk
```

## Provide privilege to the splunk service account. 

```
oc adm policy add-scc-to-user privileged system:serviceaccount:splunk:splunk
```

## From the splunk_openshift folder, deploy the standalone yaml:

```
oc apply -f standalone
```

## Pull Splunk Red Hat images

https://access.redhat.com/RegistryAuthentication

Splunk builds red hat base images to ensure we are certified in the Red Hat container catalog. This provides customers with a low friction adoption path, as they will generally mandate red hat base os for improved security vs other OS options. 

```
docker login registry.connect.redhat.com
```

https://access.redhat.com/containers/?tab=images&get-method=red-hat-login#/registry.connect.redhat.com/splunk/sck101

https://docs.openshift.com/container-platform/3.11/install_config/registry/accessing_registry.html

```
docker pull registry.connect.redhat.com/splunk/sck101
```
```
docker tag registry.connect.redhat.com/splunk/sck101 matthewmodestino/sck101
docker push matthewmodestino/sck101
```

```
oc login https://192.168.99.108:8443 --token=GJtkfdoEek6H0qSUbM4xuk5M5Diy3XiS7C-FIkq6CO4
```

```
docker login -u admin -p GJtkfdoEek6H0qSUbM4xuk5M5Diy3XiS7C-FIkq6CO4 docker-registry-default.192.168.99.108.nip.io
```

# Deploy Splunk Connect for Kubernetes

I have provided yaml files that I have rendered using “helm template” and updated them to run in Openshift. The main configurations are: 

Create Service Accounts and Provide appropriate RBAC
logging pods need root to access host file system and /var/log/containers, etc
objects pod needs proper rbac to collect from the Kubernetes API. 
metrics daemonset needs permissions to talk to the kubelet & API.


Navigate to the sck_openshift/charts folder

```
oc get nodes -o wide
```

Note your Openshift node’s internal-IP. We will update our metrics yamls to use this IP. 

Navigate to ../sck_openshift/charts/splunk-kubernetes-metrics/templates

vi configmap.yaml and update the node_name parameter with your node’s internal-IP

```
  <source>
      @type kubernetes_metrics
      tag kube.*
      #node_name "#{ENV['SPLUNK_HEC_HOST']}"
      node_name "10.0.2.15"
      kubelet_port 10250
      use_rest_client_ssl true
      insecure_ssl true
      cluster_name minishift
    </source>
```

In order to deploy successfully, our service accounts need to be provided elevated permissions to collect logs from the ocp node and to connect to the kubelet on the ocp node. 

```
oc adm policy add-scc-to-user privileged system:serviceaccount:splunk:splunk-kubernetes-logging

oc adm policy add-scc-to-user privileged system:serviceaccount:splunk:splunk-kubernetes-metrics
```

Now navigate back to sck_openshift/charts/


and deploy your manifests. 

```
oc apply -f splunk-kubernetes-logging/templates/
```

```
oc apply -f splunk-kubernetes-objects/templates/
```
```
oc apply -f splunk-kubernetes-metrics/templates/
```





