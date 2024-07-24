# SOME-DATA-MONITORING β

### BIGQUERY

- Query data from `region-eu.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
- OUTPUT: VIEW some_data_monitoring.BigQuery (BigQuery.sql)

### GCP

> You must have [Set up Cloud Billing data export to BigQuery](https://cloud.google.com/billing/docs/how-to/export-data-bigquery-setup) first.

- Get *preprocessed* data from Billing export.
- FREQUENCY: Once an hour.
- OUTPUT: some_data_monitoring.billing


## HOW TO

### LOCALLY

In order to test code locally, you need to export this environnement variable: 
```shell
export GCP_SA=$(cat secret/some-data-monitoring.json)
```

You have to create a local `venv` environnement in which the code must be run: 
```shell
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install -r src/requirements.txt
```

Then you can run the following command: 
```shell
$ python src/[TASK].py --conf conf/some-data-monitoring.yaml
```

### END TO END ON MINIKUBE

Make sure to have Airflow2 (pip install "apache-airflow[kubernetes]") & Minikube ([minikube_latest_amd64.deb](https://storage.googleapis.com/minikube/releases/latest/minikube_latest_amd64.deb)) installed on your machine. 

Start your airflow webserver & scheduler: 
```shell
$ airflow webserver -p PORT
$ airflow scheduler
```

(from project root directory) Start your minikube, create namespace, ConfigMap and Secret, deploy dag and build code:
```shell
$ ./dev/deploy_local.sh full
``` 

Open the Airflow webserver [HERE](http://127.0.0.1:PORT/home)
