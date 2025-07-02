from kubernetes import client
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_pod_status(pod_name, namespace="default"):
    try:
        api = client.CoreV1Api()

        # Get the Pod object
        pod = api.read_namespaced_pod(name=pod_name, namespace=namespace)

        if pod.status.phase == "Running":
            return True

    except client.exceptions.ApiException as e:
        if e.status == 404:
            logging.info(f"Pod '{pod_name}' not found in namespace '{namespace}'.")
        else:
            logging.error(f"Exception when reading Pod: {e}")

    return False


def create_log_pod(pod_name, namespace):
    pvc_name = f"{pod_name}-pvc"
    running_date = datetime.now()

    # Create a Pod with a volume mount
    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(name=pod_name),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    name=pod_name,
                    image="busybox",
                    command=[
                        "/bin/sh",
                        "-c",
                        f"echo '{running_date} Writing log...' >> /log/checkmydump/queries.log; sleep 3600",
                    ],  # TODO see if there is a better way and/or improve and use params, or env var for log file
                    volume_mounts=[client.V1VolumeMount(name=pvc_name, mount_path="/log/checkmydump")],
                )
            ],
            volumes=[
                client.V1Volume(
                    name=pvc_name,
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name),
                )
            ],
            restart_policy="Never",
        ),
    )
    api = client.CoreV1Api()
    try:
        api.create_namespaced_pod(namespace=namespace, body=pod)
    except client.exceptions.ApiException as e:
        logging.error(f"Exception when create log pod: {e}")


def delete_pod(name, namespace):
    try:
        api = client.CoreV1Api()

        # Delete the pod
        api.delete_namespaced_pod(name=name, namespace=namespace, body=client.V1DeleteOptions(grace_period_seconds=0))
    except client.exceptions.ApiException as e:
        logging.error(f"Exception when delete log pod: {e}")
