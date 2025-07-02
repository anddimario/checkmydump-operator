from kubernetes import client
from kubernetes.stream import stream
import logging

logger = logging.getLogger(__name__)


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
