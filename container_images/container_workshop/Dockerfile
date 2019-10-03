#Debian 9 base
#FROM splunk/splunk:latest

#Redhat UBI
FROM splunk/splunk:7.3.2-redhat

#Seed apps for install
COPY ta_container_workshop.tgz /tmp/
COPY splunk-app-for-infrastructure_141.tgz /tmp/
COPY splunk-business-flow_102.tgz /tmp
#COPY splunk-add-on-for-amazon-web-services_450.tgz /tmp/


#Copy in base default.yml
COPY default.yml /tmp/defaults/
