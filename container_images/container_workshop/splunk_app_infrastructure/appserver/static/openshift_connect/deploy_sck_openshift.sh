#!/bin/bash

function print_info {
    echo -e "\033[32m\n $* \n\033[0m"
}

function print_error {
    echo -e "\033[31m\n $* \n\033[0m"
}

function sed_inplace {
    if [ "$(uname -s)" = "Darwin" ]; then
        sed -i '' "$1" "$2"
    else
        sed -i "$1" "$2"
    fi
}

function sed_script_inplace {
    if [ "$(uname -s)" = "Darwin" ]; then
        sed -i '' -e "$1" "$2"
    else
        sed -i -e "$1" "$2"
    fi
}

# check for helm
if ! hash helm 2>/dev/null; then
	print_error "Helm required. Exiting ..."
	exit 1
fi

if [ -f "openshift_connect_template.yaml" ]; then
    # rename yaml file
    mv openshift_connect_template.yaml values.yaml
else
    print_error "openshift_connect_template.yaml was not downloaded. Exiting..."
    exit 1
fi

# Update template for values.yaml
if [ -n "$MONITORING_MACHINE" ]; then
    sed_inplace "s/\${monitoring_machine}/${MONITORING_MACHINE}/" values.yaml
else
    print_error "Undefined environment variable MONITORING_MACHINE ..."
    exit 1
fi

if [ -n "$HEC_TOKEN" ]; then
    sed_inplace "s/\${hec_token}/${HEC_TOKEN}/" values.yaml
else
    print_error "Undefined environment variable HEC_TOKEN ..."
    exit 1
fi

if [ -n "$HEC_PORT" ]; then
    sed_inplace "s/\${hec_port}/${HEC_PORT}/" values.yaml
else
    print_error "Undefined environment variable HEC_PORT ..."
    exit 1
fi

if [ -n "$METRICS_INDEX" ]; then
    sed_inplace "s/\${metrics_index}/${METRICS_INDEX}/" values.yaml
else
    print_error "Undefined environment variable METRICS_INDEX ..."
    exit 1
fi

if [ -n "$LOG_INDEX" ]; then
    sed_inplace "s/\${log_index}/${LOG_INDEX}/" values.yaml
else
    print_error "Undefined environment LOG_INDEX x ..."
    exit 1
fi

if [ -n "$META_INDEX" ]; then
    sed_inplace "s/\${meta_index}/${META_INDEX}/" values.yaml
else
    print_error "Undefined environment variable META_INDEX ..."
    exit 1
fi

if [ -n "$KUBELET_PROTOCOL" ]; then
    if [ "${KUBELET_PROTOCOL}" = "http" ]; then
        sed_inplace "s/\${kubelet_port}/10255/" values.yaml
        sed_inplace "s/\${use_https}/false/" values.yaml
    elif [ "${KUBELET_PROTOCOL}" = "https" ]; then
        sed_inplace "s/\${kubelet_port}/10250/" values.yaml
        sed_inplace "s/\${use_https}/true/" values.yaml
    else
        print_error "Incorrect kubelet port value ..."
        exit 1
    fi
else
    print_error "Undefined environment variable KUBELET_PROTOCOL ..."
    exit 1
fi

if [ -n "$GLOBAL_HEC_INSECURE_SSL" ]; then
    sed_inplace "s/\${global_hec_insecure_ssl}/${GLOBAL_HEC_INSECURE_SSL}/" values.yaml
else
    print_error "Undefined environment variable GLOBAL_HEC_INSECURE_SSL ..."
    exit 1
fi

if [ -n "$METRICS_INSECURE_SSL" ]; then
    sed_inplace "s/\${metrics_insecure_ssl}/${METRICS_INSECURE_SSL}/" values.yaml
else
    print_error "Undefined environment variable METRICS_INSECURE_SSL ..."
    exit 1
fi

if [ -n "$OBJECTS_INSECURE_SSL" ]; then
    sed_inplace "s/\${objects_insecure_ssl}/${OBJECTS_INSECURE_SSL}/" values.yaml
else
    print_error "Undefined environment variable OBJECTS_INSECURE_SSL ..."
    exit 1
fi

if [ -n "$JOURNALD_PATH" ]; then
    sed_inplace "s#\${journal_log_path}#${JOURNALD_PATH}#" values.yaml
else
    print_error "Undefined environment variable JOURNALD_PATH ..."
    exit 1
fi

if [ -n "$SAI_SCK_PROJECT" ]; then
    sck_project=$SAI_SCK_PROJECT
else
    print_error "Undefined environment variable SAI_SCK_PROJECT ..."
    exit 1
fi

if [ -n "$CLUSTER_NAME" ]; then
    sed_inplace "s/\${cluster_name}/${CLUSTER_NAME}/" values.yaml
else
    print_error "Undefined environment variable CLUSTER_NAME ..."
    exit 1
fi

# set the core openshift objects
if [ -n "$CORE_OBJ" ]; then
    oc_core_objects=$CORE_OBJ
    IFS=','
    map_in_lists=""
    for each in $oc_core_objects
    do
        if [ "$each" == "events" ]; then
            map_in_lists+="{\"name\":\"$each\", \"mode\":\"watch\"}"
        else
            map_in_lists+="{\"name\":\"$each\", \"interval\":\"60s\"}"
        fi
        map_in_lists+=","
    done
    sed_inplace "s/\${openshift_core_objects}/[$map_in_lists]/"  values.yaml
else
    print_error "Undefined environment variable CORE_OBJ ..."
    exit 1
fi

# set the apps openshift objects
if [ -n "$APPS_OBJ" ]; then
    oc_apps_objects=$APPS_OBJ
    IFS=','
    map_in_lists=""
    for each in $oc_apps_objects
    do
        map_in_lists+="{\"name\":\"$each\", \"interval\":\"60s\"},"
    done
    sed_inplace 's/${openshift_apps_objects_clause}/apps:\
      v1:\
        ${openshift_apps_objects}/' values.yaml
    sed_inplace "s/\${openshift_apps_objects}/[$map_in_lists]/" values.yaml
else
    sed_inplace 's/ *${openshift_apps_objects_clause}//' values.yaml
fi

# Check if we just want to create the manifests
# Do not create project, service accounts or delopy SCK
sck_download_only="false"
if [ -n "${SCK_DOWNLOAD_ONLY}" ]; then
    sck_download_only="${SCK_DOWNLOAD_ONLY}"
fi

if [ "${sck_download_only}" != "true" ]; then
    # create a project and switch to it
    print_info "Creating new Openshift project: ${sck_project} ..."
    oc adm new-project "$sck_project" --node-selector=""
    if [ $? -ne 0 ]; then
	    print_error "Failed to create new Openshift project: ${sck_project} ..."
	    exit 1
    fi
    oc project "$sck_project"
fi

# create directory for charts
mkdir -p rendered-charts

# render templates using helm
print_info "Rendering Helm templates ..."
helm template --name=sck-rendered --namespace="$sck_project" --values values.yaml --output-dir ./rendered-charts splunk-connect-for-kubernetes.tgz
if [ $? -ne 0 ]; then
    print_error "Failed to render SCK charts ..."
    exit 1
fi

# Insert securityContext and serviceAccount into daemonset.yaml for logging
daemonsetyaml='./rendered-charts/splunk-connect-for-kubernetes/charts/splunk-kubernetes-logging/templates/daemonset.yaml'
sed_script_inplace '/imagePullPolicy/a\
\        securityContext:\
\          privileged: true\
\          runAsUser: 0'$'\n' "$daemonsetyaml"

sed_script_inplace '/    spec:/a \
\      serviceAccountName: splunk-kubernetes-logging'$'\n' "$daemonsetyaml"

# Insert securityConntext into deployment.yaml for metrics
deploymentyaml='./rendered-charts/splunk-connect-for-kubernetes/charts/splunk-kubernetes-metrics/templates/deployment.yaml'
sed_script_inplace '/imagePullPolicy/a\
\        securityContext:\
\          privileged: true\
\          runAsUser: 0'$'\n' "$deploymentyaml"

# insert securityConntext into deploymentMetricsAggregator.yaml for metrics
deploymentaggyaml='./rendered-charts/splunk-connect-for-kubernetes/charts/splunk-kubernetes-metrics/templates/deploymentMetricsAggregator.yaml'
sed_script_inplace '/imagePullPolicy/a\
\        securityContext:\
\          privileged: true\
\          runAsUser: 0'$'\n' "$deploymentaggyaml"

# insert entity_types into configMap.yaml for metrics
configmapyaml='./rendered-charts/splunk-connect-for-kubernetes/charts/splunk-kubernetes-metrics/templates/configMap.yaml'
sed_script_inplace '/\/source/a\
\    <filter kube.node.**>\
\      @type record_modifier\
\      <record>\
\        entity_type k8s_node_ocp\
\      </record>\
\    </filter>\
\    <filter kube.pod.**>\
\      @type record_modifier\
\      <record>\
\        entity_type k8s_pod_ocp\
\      </record>\
\    </filter>'$'\n' "$configmapyaml"

if [ "${sck_download_only}" != "true" ]; then
    # Create service account and add privileged permissions for logging
    print_info "Creating service account: splunk-kubernetes-logging ..."
    oc create sa splunk-kubernetes-logging
    oc adm policy add-scc-to-user privileged "system:serviceaccount:${sck_project}:splunk-kubernetes-logging"
    if [ $? -ne 0 ]; then
	    print_error "Failed to add privileged policy to serivce account splunk-kubernetes-logging ..."
	    exit 1
    fi

    # Create service account and add privileged permissions for metrics
    print_info "Creating service account: splunk-kubernetes-metrics ..."
    oc create sa splunk-kubernetes-metrics
    oc adm policy add-scc-to-user privileged "system:serviceaccount:${sck_project}:splunk-kubernetes-metrics"
    if [ $? -ne 0 ]; then
	    print_error "Failed to add privileged policy to serivce account splunk-kubernetes-metrics ..."
	    exit 1
    fi

    # Apply Openshift templates for logs and objects ..
    print_info "Applying SCK templates for logging ..."
    oc apply -f ./rendered-charts/splunk-connect-for-kubernetes/charts/splunk-kubernetes-logging/templates/
    print_info "Applying SCK templates for objects ..."
    oc apply -f ./rendered-charts/splunk-connect-for-kubernetes/charts/splunk-kubernetes-objects/templates/

    # Apply Openshift templates for metrics ..
    print_info "Applying SCK templates for metrics ..."
    oc apply -f ./rendered-charts/splunk-connect-for-kubernetes/charts/splunk-kubernetes-metrics/templates/

    print_info "Finished deploying SCK ..."
else
    print_info "Finished rendering templates ..."
fi
