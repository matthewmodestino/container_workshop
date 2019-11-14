# A Splunker’s guide to containers

The following hands on walkthroughs are meant to enable Splunk users to experience various container concepts and Splunk product patterns seen in the wild. 

> This content is NOT Splunk Supported configuration or meant to be production deployment guidance. Don't let this stop you from exploring!
 
# Getting Started

> Note: we will be running Linux containers in all labs. 

The following labs expect Microk8s will be used as the container environments. This will help ensure content can be followed locally on your laptop.

In theory, you should be able to follow these on any properly configured Docker, Kubernetes or Openshift environment, with sufficient Splunk & Container platform knowledge. 

If you run into issues, I will do my best to support you via Github Issues or Splunk User Group Slack (splk.it/slack) in the #docker or #kubernetes or #Openshift channels. 


https://microk8s.io/docs/


## Sign up/Sign into docker hub (Optional)
You will want to have an account on dockerhub to allow you to share and publish docker images.

https://hub.docker.com/signup

## Pull the Workshop repo
All the files you will need to run the demos are contained here.

git clone https://github.com/matthewmodestino/container_workshop


## Docker Images
In the following labs, we will deploy splunk enterprise standalone instance - built on Red Hat’s Universal Base Image - that have been pre-configured to make use of k8s data, immediately. If you would like to customize or control the behaviour of the app, you can create your own images, and use docker-splunk's app install options. 

```
microk8s.docker build -t matthewmodestino/container_workshop:8.0.0 -f ./Dockerfile .
```

```
microk8s.docker push matthewmodestino/container-workshop:8.0.0
```

# Labs

Now that you have your environments ready, you can dive into the labs. For beginners, I recommend doing them in succession, as knowledge in Docker images and Docker concepts translates well into k8s and Openshift, but feel free to choose your own adventure! 

Next: [This way to the lab!](01-start-here.md)
