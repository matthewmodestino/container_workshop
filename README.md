# A Splunker’s guide to containers

The following hands on walkthroughs are meant to enable Splunk users to experience various container concepts and Splunk product patterns seen in the wild. 

From monitoring container platforms with Splunk, to deploying Splunk in container environments, you will explore common integrations in today’s containerized environments. We hope it will inspire you to join the growing community of Splunkers helping shape the future of Splunk in containerized environments!

The following content is NOT Splunk Supported configuration or meant to be production deployment guidance. Please consult Splunk Documentation or your Splunk account team & Professional Services for advanced production support. 
Getting Started
Note: we will be running Linux containers in all labs. 

The following labs expect Docker Desktop and Minishift will be used as the container environments. This will help ensure content can be followed locally on your laptop.

In theory, you should be able to follow these on any properly configured Docker, Kubernetes or Openshift environment, with sufficient Splunk & Container platform knowledge. 

If you run into issues, I will do my best to support you via Github Issues or Splunk User Group Slack (splk.it/slack) in the #docker or #kubernetes or #Openshift channels. 

##Install Docker for Mac or Windows 
For the Docker and Kubernetes labs, we will use Docker Desktop. The following labs and content were developed against Docker Desktop for Mac, but SHOULD work on Windows or any properly configured Docker or Kubernetes environment. 

Mac
https://docs.docker.com/docker-for-mac/

Windows
https://docs.docker.com/docker-for-windows/

##Sign up/Sign into docker hub (Optional)
You will want to have an account on dockerhub to allow you to share and publish docker images.

https://hub.docker.com/signup

##Pull the Workshop repo
All the files you will need to run the demos are contained here.

git clone https://github.com/matthewmodestino/container_workshop
Docker Images
In the following labs, we will deploy a splunk enterprise standalone instance, built on Red Hat’s Universal Base Image, that has been pre-configured to install metrics workspace and a custom app with configs to use with Splunk Connect for Kubernetes. 


```
docker build -t matthewmodestino/container-workshop:7.2.6-redhat -f ./Dockerfile .
```

```
docker push matthewmodestino/container-workshop:7.2.6-redhat
```

```
docker build -t matthewmodestino/container-workshop:7.2.6-redhat -f ./Dockerfile .
Sending build context to Docker daemon  20.64MB
Step 1/3 : FROM splunk/splunk:7.2.6-redhat
7.2.6-redhat: Pulling from splunk/splunk
ed6b7e8623ef: Pull complete 
5b86d995ed7f: Pull complete 
590775e2dc38: Pull complete 
c3e3238f19f9: Pull complete 
62dfee69ddd6: Pull complete 
028bcc8f36e7: Pull complete 
e6b8e8e686ab: Pull complete 
4faa98fbfe5a: Pull complete 
cfe8b21f9c2e: Pull complete 
7cfc59345f7a: Pull complete 
8dad836b6dab: Pull complete 
98d06aecab78: Pull complete 
Digest: sha256:7cdb5cd20dceace95213426f40efdd8c7fc209d6ef2ff1b0a2a6e2a640b1ac1b
Status: Downloaded newer image for splunk/splunk:7.2.6-redhat
 ---> 0e7bb95b6220
Step 2/3 : COPY ta_container_workshop.tgz /tmp/
 ---> 46fa7e8487d2
Step 3/3 : COPY splunk-metrics-workspace_101.tgz /tmp/
 ---> 390425126202
Successfully built 390425126202
Successfully tagged matthewmodestino/container-workshop:7.2.6-redhat
```






