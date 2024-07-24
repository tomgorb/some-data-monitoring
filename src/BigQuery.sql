SELECT
  DATE(creation_time) AS creation_date,
  project_id,
  user_email,
  total_bytes_processed,
  total_bytes_billed,
  TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) AS job_duration_ms,
  total_slot_ms,
  CASE
    WHEN total_slot_ms = 0 THEN NULL
    WHEN total_slot_ms IS NULL THEN NULL
    WHEN TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) IS NULL THEN NULL
    ELSE TIMESTAMP_DIFF(end_time, start_time, MILLISECOND)/total_slot_ms
END
  AS approx_nb_slots,
  CASE
    WHEN STARTS_WITH(destination_table.dataset_id, "_") THEN "_"
    ELSE destination_table.dataset_id
END
  AS destination_dataset_id,
  destination_table.table_id AS destination_table_id,
  ((
    SELECT
      DISTINCT dataset_id
    FROM
      UNNEST(referenced_tables) )) AS referenced_dataset_id,
  total_bytes_billed/POW(10,12)*6.25 AS dollar
FROM
  `region-eu.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE
  job_type = 'QUERY'
  AND statement_type != 'SCRIPT'