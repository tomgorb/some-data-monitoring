import os
import logging
import importlib
from datetime import datetime, timedelta

from kubernetes.client import models as k8s
from airflow.kubernetes.secret import Secret
from airflow.models import DAG 
from airflow.providers.cncf.kubernetes.operators.pod import (
    KubernetesPodOperator,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

PROJECT_NAME = "some-data-monitoring"

dag_info = importlib.import_module(f"{PROJECT_NAME}.dag_variables")

DAG_MD = f"""\
# Some Data Monitoring

All tasks are pushing some data into a common BigQuery project.

Code is running in the {dag_info.K8S_NS} namespace with the {dag_info.K8S_SA} ksa in the composer cluster.

## Versions
- **Image**: {dag_info.IMAGE_VERSION}
- **DAG**: {dag_info.DAG_VERSION}

"""


class DagBuilder:
    PATH_SECRET = "/secret"
    SECRET_NAME = PROJECT_NAME
    SECRET_KEY = f"{SECRET_NAME}.json"

    PATH_CONF = "/conf"
    CONF_NAME = PROJECT_NAME
    CONF_KEY = f"{CONF_NAME}.yaml"

    def __init__(self):
        self.image = f"{dag_info.IMAGE_REPOSITORY}:{dag_info.IMAGE_VERSION}"

        self.env_vars = {
            'OWNER': 'tomgorb'
        }

        volume_mount = k8s.V1VolumeMount(mount_path=DagBuilder.PATH_CONF, name=DagBuilder.CONF_NAME)
        volume = k8s.V1Volume(
                name=DagBuilder.CONF_NAME,
                config_map=k8s.V1ConfigMapVolumeSource(name=DagBuilder.CONF_NAME),
            )
 
        self.volume_mounts = [
            volume_mount
        ]

        self.volumes = [
            volume
        ]

        self.secrets = [

            Secret("env", "GCP_SA", DagBuilder.SECRET_NAME, DagBuilder.SECRET_KEY)

                    # Secret(
                    #     deploy_type="volume",
                    #     # Path where we mount the secret as volume
                    #     deploy_target="/var/secrets/google",
                    #     # Name of Kubernetes Secret
                    #     secret="service-account",
                    #     # Key in the form of service account file name
                    #     key="service-account.json",
                    # )
        ]

    @staticmethod
    def create_monitoring_dag(dag_id: str, start_date: datetime) -> DAG:
        default_args = {"depends_on_past": False}

        _dag = DAG(
            dag_id=dag_id,
            schedule_interval='@hourly',
            start_date=start_date,
            default_args=default_args,
            max_active_runs=1,
            catchup=False,
            doc_md=DAG_MD,
            tags=["monitoring", "tools"],
        )
        return _dag

    def create_data_task(self, dag_id: str, task_name: str):
        execute_command = [
            "python3",
            "src/{}.py".format(task_name),
            "--conf",
            os.path.join(DagBuilder.PATH_CONF, DagBuilder.CONF_KEY),
        ]

        container_resources = k8s.V1ResourceRequirements(
            limits={"memory": "256Mi", "cpu": "300m"},
        )

        return KubernetesPodOperator(
            task_id=task_name,
            name=task_name,
            cmds=execute_command,
            container_resources=container_resources,
            image=self.image,
            image_pull_policy=dag_info.IMAGE_PULL_POLICY,
            namespace=dag_info.K8S_NS,
            service_account_name=dag_info.K8S_SA,
            env_vars=self.env_vars,
            startup_timeout_seconds=300,
            volume_mounts=self.volume_mounts,
            volumes=self.volumes,
            secrets=self.secrets,
            retries=1,
            retry_delay=timedelta(minutes=1),
            execution_timeout=timedelta(minutes=30),
            dag=globals()[dag_id],
        )

    def create_dag(self):

        dag_id = "some-data-monitoring"
        globals()[dag_id] = self.create_monitoring_dag(dag_id, datetime(2024, 4, 24))

        for task_name in [
            "gcp",
        ]:
            self.create_data_task(dag_id, task_name)


dag_builder = DagBuilder()
dag_builder.create_dag()
