from kubernetes import client
import logging

logger = logging.getLogger(__name__)


def init_log_storage(name, namespace):
    api = client.CoreV1Api()
    pvc_name = f"{name}-logger-pvc"
    pv_name = f"{name}-logger-pv"

    # Create Persistent Volume (PV)
    pv = client.V1PersistentVolume(
        api_version="v1",
        kind="PersistentVolume",
        metadata=client.V1ObjectMeta(name=pv_name),
        spec=client.V1PersistentVolumeSpec(
            capacity={"storage": "1Gi"},
            access_modes=["ReadWriteOnce"],
            persistent_volume_reclaim_policy="Retain",
            host_path=client.V1HostPathVolumeSource(path="/mnt/data"),  # Local path on node
            storage_class_name="standard",
        ),
    )

    try:
        api.create_persistent_volume(pv)
    except client.exceptions.ApiException as e:
        logging.error(f"Exception when create pv for {name} to store the log: {e}")
        return False

    # Create Persistent Volume Claim (PVC)
    pvc = client.V1PersistentVolumeClaim(
        api_version="v1",
        kind="PersistentVolumeClaim",
        metadata=client.V1ObjectMeta(name=pvc_name),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            resources=client.V1ResourceRequirements(requests={"storage": "1Gi"}),
            volume_name=pv_name,  # Bind to the above PV
        ),
    )

    try:
        api.create_namespaced_persistent_volume_claim(namespace=namespace, body=pvc)
    except client.exceptions.ApiException as e:
        logging.error(f"Exception when create pvc for {name} to store the log: {e}")
        return False

    logging.info(f"✅ Log storage {pvc_name} Created")
    return True


def delete_log_storage(name, namespace):
    api = client.CoreV1Api()
    pvc_name = f"{name}-logger-pvc"
    pv_name = f"{name}-logger-pv"

    try:
        api.delete_namespaced_persistent_volume_claim(
            name=pvc_name,
            namespace=namespace,
            body=client.V1DeleteOptions(),  # Optional, can pass grace_period_seconds
        )
        logging.info(f"PVC '{pvc_name}' deleted.")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            logging.info(f"PVC {pvc_name} not found.")
        else:
            raise

    try:
        api.delete_persistent_volume(
            name=pv_name,
            body=client.V1DeleteOptions(),
        )
        logging.info(f"PV '{pv_name}' deleted.")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            logging.info(f"PV {pv_name} not found.")
        else:
            raise
