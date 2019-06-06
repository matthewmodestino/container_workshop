# A Splunker’s guide to containers

The following hands on walkthroughs are meant to enable Splunk users to experience various container concepts and Splunk product patterns seen in the wild. 

> This content is NOT Splunk Supported configuration or meant to be production deployment guidance. Don't let this stop you from exploring!
 
# Getting Started

> Note: we will be running Linux containers in all labs. 

The following labs expect Docker Desktop and Minishift will be used as the container environments. This will help ensure content can be followed locally on your laptop.

In theory, you should be able to follow these on any properly configured Docker, Kubernetes or Openshift environment, with sufficient Splunk & Container platform knowledge. 

If you run into issues, I will do my best to support you via Github Issues or Splunk User Group Slack (splk.it/slack) in the #docker or #kubernetes or #Openshift channels. 

## Install Docker for Mac or Windows 
To complete the Docker and Kubernetes labs and to work with docker images, we will use Docker Desktop. The following labs and content were developed against Docker Desktop for Mac, but SHOULD work on Windows or any properly configured Docker or Kubernetes environment. 


Mac
https://docs.docker.com/docker-for-mac/

Windows
https://docs.docker.com/docker-for-windows/


## Install Minishift

To complete the Openshift lab, we will use minishift, which we will build a openshift vm using virtualbox. 

### Install Virtualbox on your Mac
https://docs.okd.io/latest/minishift/getting-started/setting-up-virtualization-environment.html#setting-up-virtualbox-driver

### Install homebrew
https://brew.sh/

### Install minishift
https://docs.okd.io/latest/minishift/getting-started/installing.html

```
brew cask install minishift
```

### start minishift


```
minishift start --vm-driver virtualbox --docker-opt log-driver=json-file 
```

Once minishift comes up, note the admin credentials. 

```
Login to server ...
Creating initial project "myproject" ...
Server Information ...
OpenShift server started.

The server is accessible via web console at:
    https://192.168.99.104:8443/console

You are logged in as:
    User:     developer
    Password: <any value>

To login as administrator:
    oc login -u system:admin
```

## Sign up/Sign into docker hub (Optional)
You will want to have an account on dockerhub to allow you to share and publish docker images.

https://hub.docker.com/signup

## Pull the Workshop repo
All the files you will need to run the demos are contained here.

git clone https://github.com/matthewmodestino/container_workshop

## Docker Images
In the following labs, we will deploy splunk enterprise standalone instances, built on Red Hat’s Universal Base Image, that have been pre-configured to install a custom add-on to use with Splunk Connect for Kubernetes data. 


```
docker build -t matthewmodestino/container-workshop:7.3.0-redhat -f ./Dockerfile .
```

```
docker push matthewmodestino/container-workshop:7.3.0-redhat
```

```
docker build -t matthewmodestino/container-workshop:7.2.6-redhat -f ./Dockerfile .
Sending build context to Docker daemon  18.94kB
Step 1/2 : FROM splunk/splunk:7.3.0-redhat
 ---> 533cc44ac5d6
Step 2/2 : COPY ta_container_workshop.tgz /tmp/
 ---> Using cache
 ---> 0396a2aaa34e
Successfully built 0396a2aaa34e
```


# Labs

Now that you have your environments ready, you can dive into the labs. For beginners, I recommend doing them in succession, as knowledge in Docker images and Docker concepts translates well into k8s and Openshift, but feel free to choose your own adventure! 


* [Docker](docs/01-docker-lab.md)
* [Kubernetes](docs/02-kubernetes-lab.md)
* [Openshift](docs/03-openshift-lab.md)



