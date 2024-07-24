import argparse
import logging
import os
import sys
import json
import yaml
import requests
from datetime import datetime, timezone
from google.oauth2 import service_account
from google.cloud import bigquery
from google.cloud.exceptions import Conflict, NotFound

logger = logging.getLogger(__name__)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Cloud Billing export (BQ) --> Looker (BQ)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--conf",
        dest="conf",
        required=False,
        help="Absolute or relative path to configuration file.",
        default="/conf/some-data-monitoring.yaml",
    )

    args, unknown = parser.parse_known_args()

    root_logger = logging.getLogger()
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.setLevel(logging.INFO)  # DEBUG
    root_logger.addHandler(console_handler)

    with open(args.conf, "r") as f:
        config = yaml.safe_load(f)

    # DEFINE BQ CLIENT
    project_id = config["google_cloud"]["project"]
    credentials = service_account.Credentials.from_service_account_info(json.loads(os.environ["GCP_SA"]))
    bq_client = bigquery.Client(project=project_id, credentials=credentials)

    # DATASET
    dataset_id = "some_data_monitoring"
    dataset_ref = bq_client.dataset(dataset_id)
    try:
        bq_client.get_dataset(dataset_ref)
    except NotFound as nf:
        logger.info(nf)
        try:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "EU"
            bq_client.create_dataset(dataset)
        except Conflict as c:
            logger.info(c)

    table_id = "billing"

    # ONCE AN HOUR IS ENOUGH
    table_ref = bq_client.dataset(dataset_id).table(table_id)
    try:
        table = bq_client.get_table(table_ref)
        if str(table.modified)[:13] == str(datetime.now(timezone.utc))[:13]:
            logger.info("Waiting for the next hour.")
            sys.exit(0)
    except Exception as e:
        logger.info(e)

    data = requests.get("https://api.exchangerate-api.com/v4/latest/USD").json()
    
    query = """ SELECT
                    CURRENT_TIMESTAMP() AS timestamp,
                    %f AS dollar2euro"""%data["rates"]["EUR"]
    job_config = bigquery.QueryJobConfig()
    job_config.destination = bq_client.dataset(dataset_id).table("dollar2euro")
    job_config.write_disposition = "WRITE_APPEND"
    query_job = bq_client.query(query, location='EU', job_config=job_config)  # API request - starts the query
    query_job.result()

    query = """ SELECT
                    service.description AS service,
                    sku.description AS sku,
                    DATE(usage_start_time) AS date,
                    ROUND(cost, 2) AS cost,
                    ROUND( (SELECT SUM(amount) FROM UNNEST(credits)), 2) AS credit
                FROM
                    `%s.%s.%s`"""%(project_id, config["google_cloud"]["billing"]["dataset"], config["google_cloud"]["billing"]["table"])
    job_config = bigquery.QueryJobConfig()
    job_config.destination = table_ref
    job_config.write_disposition = "WRITE_TRUNCATE"
    query_job = bq_client.query(query, location='EU', job_config=job_config)
    query_job.result()

    logger.info("upload to BigQuery OK")
    