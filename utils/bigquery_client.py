import logging
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)

try:
    from google.cloud import bigquery
    from google.api_core.exceptions import NotFound, GoogleAPIError
except ImportError:
    bigquery = None  # type: ignore
    NotFound = Exception
    GoogleAPIError = Exception


class BigQueryClient:
    def __init__(self, project_id: str,
                 credentials_file: Optional[str] = None) -> None:
        self.project_id = project_id
        if bigquery is None:
            raise ImportError("google-cloud-bigquery is not installed")
        if credentials_file:
            self._client = bigquery.Client.from_service_account_json(
                credentials_file, project=project_id
            )
        else:
            self._client = bigquery.Client(project=project_id)
        logger.debug("BigQuery client initialised for project %s", project_id)

    # ── dataset operations ─────────────────────────────────────────────

    def dataset_exists(self, dataset_id: str) -> bool:
        try:
            self._client.get_dataset(dataset_id)
            return True
        except NotFound:
            return False

    def create_dataset(self, dataset_id: str, location: str = "US") -> None:
        ds = bigquery.Dataset(f"{self.project_id}.{dataset_id}")
        ds.location = location
        self._client.create_dataset(ds, exists_ok=True)
        logger.info("Dataset %s.%s ready", self.project_id, dataset_id)

    def list_datasets(self) -> list[str]:
        return [ds.dataset_id for ds in self._client.list_datasets()]

    # ── table operations ───────────────────────────────────────────────

    def table_exists(self, dataset_id: str, table_id: str) -> bool:
        try:
            self._client.get_table(f"{self.project_id}.{dataset_id}.{table_id}")
            return True
        except NotFound:
            return False

    def list_tables(self, dataset_id: str) -> list[str]:
        return [t.table_id for t in
                self._client.list_tables(f"{self.project_id}.{dataset_id}")]

    def get_table_schema(self, dataset_id: str, table_id: str) -> list[dict]:
        table = self._client.get_table(
            f"{self.project_id}.{dataset_id}.{table_id}"
        )
        return [{"name": f.name, "type": f.field_type, "mode": f.mode}
                for f in table.schema]

    # ── query operations ───────────────────────────────────────────────

    def run_query(self, sql: str,
                  params: Optional[dict[str, Any]] = None) -> list[dict]:
        job = self._client.query(sql)
        rows = list(job.result())
        logger.info("Query returned %d rows, processed %s bytes",
                    len(rows), job.total_bytes_processed)
        return [dict(row) for row in rows]

    def run_query_iter(self, sql: str) -> Iterator[dict]:
        job = self._client.query(sql)
        for row in job.result():
            yield dict(row)

    def insert_rows(self, dataset_id: str, table_id: str,
                    rows: list[dict]) -> list[dict]:
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        errors = self._client.insert_rows_json(table_ref, rows)
        if errors:
            logger.error("Insert errors: %s", errors)
        else:
            logger.info("Inserted %d rows into %s", len(rows), table_ref)
        return errors
