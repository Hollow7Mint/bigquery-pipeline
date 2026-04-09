import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from google.cloud import compute_v1
    from google.api_core.exceptions import NotFound
except ImportError:
    compute_v1 = None  # type: ignore
    NotFound = Exception


class ComputeClient:
    def __init__(self, project_id: str, zone: str,
                 credentials_file: Optional[str] = None) -> None:
        self.project_id = project_id
        self.zone       = zone
        if compute_v1 is None:
            raise ImportError("google-cloud-compute is not installed")
        self._instances = compute_v1.InstancesClient()
        self._operations = compute_v1.ZoneOperationsClient()
        logger.debug("Compute client for %s/%s", project_id, zone)

    def _wait_for_operation(self, operation_name: str,
                            timeout: int = 300) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            op = self._operations.get(project=self.project_id,
                                      zone=self.zone,
                                      operation=operation_name)
            if op.status == compute_v1.Operation.Status.DONE:
                if op.error:
                    raise RuntimeError(f"Operation failed: {op.error}")
                return
            time.sleep(5)
        raise TimeoutError(f"Operation {operation_name} timed out")

    def list_instances(self, filter_expr: str = "") -> list[dict[str, Any]]:
        request = compute_v1.ListInstancesRequest(
            project=self.project_id, zone=self.zone, filter=filter_expr
        )
        instances = []
        for inst in self._instances.list(request=request):
            instances.append({
                "name":   inst.name,
                "status": inst.status,
                "machine_type": inst.machine_type.split("/")[-1],
                "zone":   self.zone,
            })
        return instances

    def get_instance(self, name: str) -> dict[str, Any]:
        inst = self._instances.get(project=self.project_id,
                                   zone=self.zone, instance=name)
        return {
            "name":         inst.name,
            "status":       inst.status,
            "machine_type": inst.machine_type.split("/")[-1],
            "network_ips":  [
                iface.network_i_p
                for iface in inst.network_interfaces
            ],
        }

    def start_instance(self, name: str) -> None:
        op = self._instances.start(project=self.project_id,
                                   zone=self.zone, instance=name)
        self._wait_for_operation(op.name)
        logger.info("Started instance %s", name)

    def stop_instance(self, name: str) -> None:
        op = self._instances.stop(project=self.project_id,
                                  zone=self.zone, instance=name)
        self._wait_for_operation(op.name)
        logger.info("Stopped instance %s", name)

    def instance_status(self, name: str) -> str:
        try:
            inst = self._instances.get(project=self.project_id,
                                       zone=self.zone, instance=name)
            return inst.status
        except NotFound:
            return "NOT_FOUND"

    def set_labels(self, name: str, labels: dict[str, str]) -> None:
        inst = self._instances.get(project=self.project_id,
                                   zone=self.zone, instance=name)
        req = compute_v1.SetLabelsInstanceRequest(
            project=self.project_id, zone=self.zone, instance=name,
            instances_set_labels_request_resource=compute_v1.InstancesSetLabelsRequest(
                label_fingerprint=inst.label_fingerprint,
                labels=labels,
            ),
        )
        op = self._instances.set_labels(request=req)
        self._wait_for_operation(op.name)
        logger.info("Labels updated for instance %s", name)
