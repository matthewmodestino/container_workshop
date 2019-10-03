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

metrics_configmap_yaml='./splunk-connect-for-kubernetes/charts/splunk-kubernetes-metrics/templates/configMap.yaml'
objects_values_yaml='./splunk-connect-for-kubernetes/charts/splunk-kubernetes-objects/values.yaml'

# check for helm
if ! hash helm 2>/dev/null; then
	print_error "Helm required. Exiting ..."
	exit 1
fi

# rename yaml file
if [ -f "kubernetes_connect_template.yaml" ]; then
    # rename yaml file
    mv kubernetes_connect_template.yaml kubernetes_connect.yaml
else
    echo "kubernetes_connect_template.yaml was not downloaded. Exiting..."
    exit 1
fi

# update template with user defined values
if [ -n "$MONITORING_MACHINE" ]; then
    sed_inplace "s/\${monitoring_machine}/$MONITORING_MACHINE/" kubernetes_connect.yaml
else
    print_error "Undefined environment variable MONITORING_MACHINE ..."
    exit 1
fi

if [ -n "$HEC_TOKEN" ]; then
    sed_inplace "s/\${hec_token}/$HEC_TOKEN/" kubernetes_connect.yaml
else
    print_error "Undefined environment variable HEC_TOKEN ..."
    exit 1
fi

if [ -n "$HEC_PORT" ]; then
    sed_inplace "s/\${hec_port}/$HEC_PORT/" kubernetes_connect.yaml
else
    print_error "Undefined environment variable HEC_PORT ..."
    exit 1
fi

if [ -n "$METRICS_INDEX" ]; then
    sed_inplace "s/\${metrics_index}/$METRICS_INDEX/" kubernetes_connect.yaml
else
    print_error "Undefined environment variable METRICS_INDEX ..."
    exit 1
fi

if [ -n "$LOG_INDEX" ]; then
    sed_inplace "s/\${log_index}/$LOG_INDEX/" kubernetes_connect.yaml
else
    print_error "Undefined environment variable LOG_INDEX ..."
    exit 1
fi

if [ -n "$META_INDEX" ]; then
    sed_inplace "s/\${meta_index}/$META_INDEX/" kubernetes_connect.yaml
else
    print_error "Undefined environment variable META_INDEX ..."
    exit 1
fi

if [ -n "$CLUSTER_NAME" ]; then
    sed_inplace "s/\${cluster_name}/$CLUSTER_NAME/" kubernetes_connect.yaml
else
    print_error "Undefined environment variable CLUSTER_NAME ..."
    exit 1
fi

if [ -n "$KUBELET_PROTOCOL" ]; then
    if [ "${KUBELET_PROTOCOL}" = "http" ]; then
        sed_inplace "s/\${kubelet_port}/10255/" kubernetes_connect.yaml
        sed_inplace "s/\${use_https}/false/" kubernetes_connect.yaml
    elif [ "${KUBELET_PROTOCOL}" = "https" ]; then
        sed_inplace "s/\${kubelet_port}/10250/" kubernetes_connect.yaml
        sed_inplace "s/\${use_https}/true/" kubernetes_connect.yaml
    else
        print_error "Incorrect kubelet port value ..."
        exit 1
    fi
else
    print_error "Undefined environment variable KUBELET_PROTOCOL ..."
    exit 1
fi

if [ -n "$GLOBAL_HEC_INSECURE_SSL" ]; then
    sed_inplace "s/\${global_hec_insecure_ssl}/${GLOBAL_HEC_INSECURE_SSL}/" kubernetes_connect.yaml
else
    print_error "Undefined environment variable GLOBAL_HEC_INSECURE_SSL ..."
    exit 1
fi

if [ -n "$METRICS_INSECURE_SSL" ]; then
    sed_inplace "s/\${metrics_insecure_ssl}/${METRICS_INSECURE_SSL}/" kubernetes_connect.yaml
else
    print_error "Undefined environment variable METRICS_INSECURE_SSL ..."
    exit 1
fi

if [ -n "$OBJECTS_INSECURE_SSL" ]; then
    sed_inplace "s/\${objects_insecure_ssl}/${OBJECTS_INSECURE_SSL}/" kubernetes_connect.yaml
else
    print_error "Undefined environment variable OBJECTS_INSECURE_SSL ..."
    exit 1
fi

if [ -n "$JOURNALD_PATH" ]; then
    sed_inplace "s#\${journal_log_path}#${JOURNALD_PATH}#" kubernetes_connect.yaml
else
    print_error "Undefined environment variable JOURNALD_PATH ..."
    exit 1
fi

# set the core kubernetes objects
if [ -n "$CORE_OBJ" ]; then
    kube_core_objects=$CORE_OBJ
    IFS=','
    map_in_lists=""
    for each in $kube_core_objects
    do
        if [ "$each" == "events" ]; then
            map_in_lists+="{\"name\":\"$each\", \"mode\":\"watch\"}"
        else
            map_in_lists+="{\"name\":\"$each\", \"interval\":\"60s\"}"
        fi
        map_in_lists+=","
    done
    sed_inplace "s/\${kubernetes_core_objects}/[$map_in_lists]/"  kubernetes_connect.yaml
fi

# set the apps kubernetes objects
if [ -n "$APPS_OBJ" ]; then
    kube_apps_objects=$APPS_OBJ
    IFS=','
    map_in_lists=""
    for each in $kube_apps_objects
    do
        map_in_lists+="{\"name\":\"$each\", \"interval\":\"60s\"},"
    done
    sed_inplace 's/${kubernetes_apps_objects_clause}/apps:\
      v1:\
        ${kubernetes_apps_objects}/' kubernetes_connect.yaml
    sed_inplace "s/\${kubernetes_apps_objects}/[$map_in_lists]/" kubernetes_connect.yaml
else
    sed_inplace 's/ *${kubernetes_apps_objects_clause}//' kubernetes_connect.yaml
fi

# untar splunk-connect for kubernetes
tar -xzf splunk-connect-for-kubernetes.tgz

# insert entity_types into configMap.yaml for metrics
sed_script_inplace '/\/source/a\
\    <filter kube.node.**>\
\      @type record_modifier\
\      <record>\
\        entity_type k8s_node\
\      </record>\
\    </filter>\
\    <filter kube.pod.**>\
\      @type record_modifier\
\      <record>\
\        entity_type k8s_pod\
\      </record>\
\    </filter>'$'\n' "$metrics_configmap_yaml"

# Use splunk-kubernetes-objects 1.1.2
sed_inplace 's/splunk\/kube-objects:1.1.0/splunk\/kube-objects:1.1.2/' "$objects_values_yaml"

# Do helm install
helm install --name=${HELM_RELEASE_NAME} --namespace=${KUBERNETES_NAMESPACE} -f kubernetes_connect.yaml ./splunk-connect-for-kubernetes

