from kubernetes import client
from kubernetes.stream import stream


def get_db_status(pod_name, namespace="default"):
    # try:
    #     api = client.CoreV1Api()

    #     pod_list = api.list_namespaced_pod(namespace=namespace)
    #     matched_pods = [
    #         pod for pod in pod_list.items if pod.metadata.name.startswith(prefix)
    #     ]
    #     return matched_pods
    # except client.exceptions.ApiException as e:
    #     print(f"Error listing pods: {e}")
    #     return []
    try:
        api = client.CoreV1Api()

        # Get the Pod object
        pod = api.read_namespaced_pod(name=pod_name, namespace=namespace)

        # Print basic status
        print(f"Pod Phase: {pod.status.phase}")
        if pod.status.phase == "Running":
            return True
        else:
            return False

        # # Optionally check conditions
        # if pod.status.conditions:
        #     for condition in pod.status.conditions:
        #         print(f"{condition.type} = {condition.status}")

        # # Check container statuses
        # for container_status in pod.status.container_statuses or []:
        #     print(f"Container {container_status.name}: Ready = {container_status.ready}")

    except client.exceptions.ApiException as e:
        if e.status == 404:
            print(f"Pod '{pod_name}' not found in namespace '{namespace}'.")
        else:
            print(f"Exception when reading Pod: {e}")


def run_queries(checkQueries, pod_name, namespace):
    # Create the command # TODO see for a better way
    pg_queries = [f'psql -U postgres -d app -c "{query}"' for query in checkQueries]
    str_pg_queries = " && ".join(pg_queries)

    command = ["/bin/sh", "-c", str_pg_queries]

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

    print("Command output:\n", resp)


def terminate_cluster(name, namespace):
    api = client.CustomObjectsApi()

    # Define the group, version, and plural for your CRD
    group = "postgresql.cnpg.io"
    version = "v1"
    plural = "clusters"  # CRDs use plural form

    api.delete_namespaced_custom_object(group=group, version=version, namespace=namespace, plural=plural, name=name)
