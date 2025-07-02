import kopf
import logging
import time

from kubernetes import client

from datetime import datetime, timezone, timedelta
from croniter import croniter
from libs.manifest import define_cluster_manifest, define_barman_manifest
from libs.storage import init_log_storage, delete_log_storage
from libs.pod import (
    get_pod_status,
    create_log_pod,
    delete_pod,
)
from libs.check import (
    run_query,
    terminate_cluster,
    get_queries,
    run_command,
)
from libs.notification import send_notification

# You can store the last run time in-memory or in annotations/state if needed
last_run_times = {}  # TODO see use better ways

# Configure logging once, ideally in your main script or a separate logger module
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for verbose output
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),  # Output to console
        # logging.FileHandler("app.log")  # Optional: Log to a file
    ],
)

logger = logging.getLogger(__name__)


@kopf.on.create("checkmydumps")
def create_fn(spec, name, namespace, logger, **kwargs):
    log_store = spec.get("logStore", False)

    if log_store:
        is_created = init_log_storage(name, namespace)
        if not is_created:
            raise kopf.PermanentError(f"Error log storage creation for {name!r}.")

    barman_manifest = define_barman_manifest(name, namespace, spec)

    # Used for deletion of the child: https://kopf.readthedocs.io/en/stable/walkthrough/deletion/
    kopf.adopt(barman_manifest)

    try:
        # Use the CustomObjectsApi to create the resource
        api = client.CustomObjectsApi()

        api.create_namespaced_custom_object(
            group="barmancloud.cnpg.io",
            version="v1",
            namespace=namespace,
            plural="objectstores",  # NOTE: this is the plural of the kind
            body=barman_manifest,
        )

        logger.info(f"✅ Create barman Object store for {name}.")
    except client.exceptions.ApiException as e:
        logger.error(f"Create barman object store for: {e}")
        raise kopf.PermanentError(f"Create barman object store for {name!r}.")


@kopf.timer("checkmydumps", interval=60.0)
async def scheduled_backup_restore(spec, name, namespace, logger, **kwargs):
    now = datetime.now(timezone.utc)

    schedule = spec.get("schedule", "0 3 * * *")  # Default: 3 AM UTC

    # Use resource-specific key
    key = f"{namespace}/{name}"
    last_run = last_run_times.get(key)

    if not last_run:
        last_run = now - timedelta(minutes=1)

    # Check if it's time to run the job again based on cron schedule
    cron = croniter(schedule, last_run)
    next_run = cron.get_next(datetime)

    if now > next_run:
        logger.info(f"⏰ Schedule matched for {name} at {now.isoformat()}. Running logic...")
        last_run_times[key] = now
        cluster_manifest = define_cluster_manifest(name, namespace, spec)

        # Used for deletion of the child: https://kopf.readthedocs.io/en/stable/walkthrough/deletion/
        kopf.adopt(cluster_manifest)

        try:
            # Use the CustomObjectsApi to create the resource
            api = client.CustomObjectsApi()

            api.create_namespaced_custom_object(
                group="postgresql.cnpg.io",
                version="v1",
                namespace=namespace,
                plural="clusters",  # NOTE: this is the plural of the kind
                body=cluster_manifest,
            )

            logger.info("✅ CNPG Cluster created successfully.")
        except client.exceptions.ApiException as e:
            if e.status == 409:
                logger.warning(f"Cluster name '{name}' already exists.")
            else:
                logger.error(f"Failed to create Cluster: {e}")


@kopf.timer("checkmydumps", interval=60.0)
async def scheduled_check_status(spec, name, namespace, logger, **kwargs):
    pod_name = (
        f"{name}-1"  # cloudnative pg add instance number, in this case we have only one instance TODO: see other cases?
    )
    # pod_name = name

    is_db_running = get_pod_status(pod_name, namespace)

    if is_db_running:
        checkQueries = get_queries(name, namespace)

        if checkQueries:
            # see if some query has the log storage, if yes, start a pod with the mounted volume
            need_to_log = [query for query in checkQueries if "logs" in query]
            logger_pod_name = f"{name}-logger"
            if len(need_to_log) > 0:
                # Start the pod used to write the log
                create_log_pod(logger_pod_name, namespace)

            log_str = ""
            notification_str = ""
            for query in checkQueries:
                success, query_output = run_query(query["query"], pod_name, namespace)

                if success and "expectedResult" in query:
                    if query["expectedResult"] != query_output and "logs" in query:
                        log_str += (
                            f"Query: {query['query']} - Expected: {query['expectedResult']} - Output: {query_output}\n"
                        )
                        # If notification to create the alert message
                        if "notification" in query:
                            notification_str += log_str

            # Write logs
            if log_str != "":
                timeout = 60  # seconds
                interval = 2  # seconds
                elapsed = 0
                # Wait for the logger container startup
                while elapsed < timeout:  # TODO see for a better way
                    is_logger_running = get_pod_status(logger_pod_name, namespace)
                    if is_logger_running:
                        break

                    time.sleep(interval)
                    elapsed += interval
                log_command = [
                    "/bin/sh",
                    "-c",
                    f"echo -e '{log_str}' >> /log/checkmydump/queries.log",
                ]  # TODO use params or env var
                run_command(log_command, logger_pod_name, namespace)

            # terminate pod log
            delete_pod(logger_pod_name, namespace)

            # send notification
            if notification_str != "":
                send_notification(notification_str, spec, namespace)

        terminate_cluster(name, namespace)


@kopf.on.delete("checkmydumps")
def on_delete(spec, name, namespace, **kwargs):
    log_store = spec.get("logStore", False)

    if log_store:
        delete_log_storage(name, namespace)
