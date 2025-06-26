import kopf
import logging
from kubernetes import client

from datetime import datetime, timezone, timedelta
from croniter import croniter
from tasks.restore import define_manifest
from tasks.check import get_db_status, run_query, terminate_cluster, get_queries

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


@kopf.timer("checkmydumps", interval=60.0)
async def scheduled_backup_restore(spec, name, namespace, logger, **kwargs):
    now = datetime.now(timezone.utc)

    dump_name = name

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
        cluster_manifest = define_manifest(dump_name, namespace, spec)

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
                logger.warning(f"Cluster name '{dump_name}' already exists.")
            else:
                logger.error(f"Failed to create Cluster: {e}")


@kopf.timer("checkmydumps", interval=60.0)
async def scheduled_check_status(spec, name, namespace, logger, **kwargs):
    pod_name = f"{name}-1"  # cloudnative pg add instance number, in this case we have only one instance
    # pod_name = name

    is_running = get_db_status(pod_name, namespace)

    if is_running:
        checkQueries = get_queries(name, namespace)

        if checkQueries:
            for query in checkQueries:
                success, query_output = run_query(query["query"], pod_name, namespace)

                # TODO compare with the result
                if success and "expectedResult" in query:
                    if query["expectedResult"] != query_output:
                        print("NO EQUAL")
                        # TODO log and alert if it's present

        terminate_cluster(name, namespace)
