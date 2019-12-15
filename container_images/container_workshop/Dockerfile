#Redhat UBI
FROM splunk/splunk:8.0.1

#Seed apps for install
COPY ta_container_workshop.tgz /tmp/
COPY splunk-app-for-infrastructure_201.tgz /tmp/
COPY splunk-add-on-for-infrastructure_201.tgz /tmp/
COPY splunk-business-flow_116.tgz /tmp/


#Copy in base default.yml
COPY default.yml /tmp/defaults/
