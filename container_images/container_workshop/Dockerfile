#Debian 9 base
#FROM splunk/splunk:latest

#Redhat UBI
FROM splunk/splunk:8.0.0

#Seed apps for install
COPY ta_container_workshop.tgz /tmp/
COPY splunk-app-for-infrastructure_200.tgz /tmp/
COPY splunk-add-on-for-infrastructure_200.tgz /tmp/
COPY splunk-business-flow_111.tgz /tmp


#Copy in base default.yml
COPY default.yml /tmp/defaults/
