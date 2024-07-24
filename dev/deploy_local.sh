#!/bin/bash
PROJECT_NAME=$(basename $(pwd))
DAG_NAME="some-data-monitoring"
AIRFLOW_DIR=~/airflow/dags/$PROJECT_NAME
MINIKUBE_CONF_PATH=~/.minikube/config
DAG_VARIABLES_FILE=dev/dag_variables.py
CONF_PATH=conf/$DAG_NAME.yaml
SECRET_PATH=secret/$DAG_NAME.json
K8S_NS=$(grep --color=never -Po 'K8S_NS = \"\K.*' $DAG_VARIABLES_FILE || true)
K8S_NS=${K8S_NS%\"}

use() {
  cat <<-EOF
      Use: CI/CD Tools

      PARAMETERS:
      ===========
          mk_* (start/stop/delete/pause/unpause)
            - minikube *
          dag:
            - Create a folder named $PROJECT_NAME into Airflow DagBag
            - Hard link all files present in dags/ folder to $AIRFLOW_DIR
            - Hard link $DAG_VARIABLES_FILE to $AIRFLOW_DIR
          code:
            - (minikube docker-env) Build python 3.x docker image (see Dockerfile)
          namespace:
            - (minikube) Create namespace
          conf:
            - (minikube) Create a ConfigMap in $K8S_NS namespace containing local configuration
            - local_src_file: $CONF_PATH
          secret:
            - (minikube) Create a Secret containing local critical configuration
              - local_src_file: $SECRET_PATH
              - secret_id: $PROJECT_NAME
          full:
            - All of the above

      OPTIONS:
      ========
          -h  Show this message

      EXAMPLES:
      =========
          ./dev/deploy_local.sh full

EOF
}

deploy_local_dag()
{
    rm -rf $AIRFLOW_DIR
    mkdir -p $AIRFLOW_DIR
    ln dags/* $AIRFLOW_DIR
    ln $DAG_VARIABLES_FILE $AIRFLOW_DIR
    echo "DAGs hard linked to" $AIRFLOW_DIR
}

deploy_local_code()
{
    IMAGE_REPOSITORY=$(grep --color=never -Po 'IMAGE_REPOSITORY = \"\K.*' "$DAG_VARIABLES_FILE" || true)
    IMAGE_VERSION=$(grep --color=never -Po 'IMAGE_VERSION = \"\K.*' "$DAG_VARIABLES_FILE" || true)
    IMAGE_REPOSITORY=${IMAGE_REPOSITORY%\"}
    IMAGE_VERSION=${IMAGE_VERSION%\"}
    eval $(minikube -p minikube docker-env)
    docker build -t $PROJECT_NAME:$IMAGE_VERSION -f build/Dockerfile .
}

create_namespace()
{
  echo "Creating" $K8S_NS "namespace" && minikube kubectl -- create namespace $K8S_NS
}

deploy_local_conf()
{
    if grep -q "yaml" <<< "$CONF_PATH"; then
      minikube kubectl -- delete configmap $DAG_NAME -n $K8S_NS
      minikube kubectl -- create configmap $DAG_NAME --from-file=$CONF_PATH -n $K8S_NS
    elif grep -q "env" <<< "$CONF_PATH"; then
      minikube kubectl -- delete configmap $DAG_NAME -n $K8S_NS
      minikube kubectl -- create configmap $DAG_NAME --from-env=$CONF_PATH -n $K8S_NS
    fi 
}

deploy_local_secret()
{
  minikube kubectl -- delete secret $DAG_NAME -n $K8S_NS
  minikube kubectl -- create secret generic $DAG_NAME --from-file=$SECRET_PATH -n $K8S_NS
}

while getopts h arg
do
  case $arg in
    h)
    use
    exit 0
    ;;
    ?)
    echo -e "\\033[31m Unknown argument \\033[0m"
    exit 1
    ;;
  esac
done

case $1 in
mk_start)
    minikube start
    ;;
mk_stop)
    minikube stop
    ;;
mk_delete)
    minikube delete
    ;;
mk_pause)
    minikube pause
    ;;
mk_unpause)
    minikube unpause
    ;;
dag)
    deploy_local_dag
    ;;
code)
    deploy_local_code
    ;;
namespace)
    create_namespace
    ;;
conf)
    deploy_local_conf
    ;;
secret)
    deploy_local_secret
    ;;
full)
    minikube delete
    minikube start
    deploy_local_dag
    deploy_local_code
    create_namespace
    deploy_local_conf
    deploy_local_secret
    ;;
*)
    echo 'Error: No Such Option'
    exit 1
    ;;
esac
