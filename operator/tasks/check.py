from kubernetes import client
from kubernetes.stream import stream
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


def run_command(command, pod_name, namespace):
    try:
        # Create API client
        v1 = client.CoreV1Api()

        # Run the command in the Pod
        resp = stream(
            v1.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            command=command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
        )
        return True, resp

    except client.exceptions.ApiException as e:
        err_str = f"Exception when run command: {e}"
        logging.error(err_str)
        return False, err_str


def run_query(query, pod_name, namespace):
    # Create the command # TODO see for a better way
    str_pg_queries = f'psql -U postgres -d app -c "{query}" -t -A'

    command = ["/bin/sh", "-c", str_pg_queries]

    success, resp = run_command(command, pod_name, namespace)

    # Check for SQL errors in the output
    if "ERROR:" in resp:
        err_str = f"SQL Error: {resp.strip()}"
        logging.error(err_str)
        return False, err_str

    return success, resp


def terminate_cluster(name, namespace):
    try:
        api = client.CustomObjectsApi()

        # Define the group, version, and plural for your CRD
        group = "postgresql.cnpg.io"
        version = "v1"
        plural = "clusters"  # CRDs use plural form

        api.delete_namespaced_custom_object(group=group, version=version, namespace=namespace, plural=plural, name=name)
    except client.exceptions.ApiException as e:
        logging.error(f"Exception when terminate cluster: {e}")


def get_queries(label, namespace):
    try:
        crd_api = client.CustomObjectsApi()

        resources = crd_api.list_namespaced_custom_object(
            group="checkmydump.com",
            version="v1alpha1",
            namespace=namespace,
            plural="checkmydumpqueries",
            label_selector=f"checkmydumps={label}",
        )

        queries = [item["spec"] for item in resources["items"]]
        return queries

    except client.exceptions.ApiException as e:
        if e.status == 404:
            logging.info(f"Queries with label '{label}' not found in namespace '{namespace}'.")
        else:
            logging.error(f"Exception when get queries: {e}")


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
        logging.error(f"Exception when create log pod: {e}")
