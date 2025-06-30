import kopf


def define_cluster_manifest(dump_name, namespace, spec):
    # Get info from spec
    db_size = spec.get("dbSize", "10G")
    source_cluster_name = spec.get("sourceClusterName", "checkmydump-test")

    return {
        "apiVersion": "postgresql.cnpg.io/v1",
        "kind": "Cluster",
        "metadata": {
            "name": dump_name,
            "namespace": namespace,
        },
        "spec": {
            "instances": 1,  # or use a variable here
            "externalClusters": [
                {
                    "name": source_cluster_name,  # must match 'bootstrap.recovery.source'
                    "plugin": {
                        "name": "barman-cloud.cloudnative-pg.io",
                        "parameters": {"barmanObjectName": dump_name, "serverName": source_cluster_name},
                    },
                }
            ],
            "bootstrap": {
                "recovery": {
                    "source": source_cluster_name,  # This source must exactly match the metadata.name of the original cluster that created the backup.
                }
            },
            "storage": {"storageClass": "standard", "size": db_size},
        },
    }


def define_barman_manifest(name, namespace, spec):
    secret_name = spec.get("secretName")
    destination_path = spec.get("destinationPath")
    endpoint_url = spec.get("endpointURL")

    if not secret_name:
        raise kopf.PermanentError(f"Secret name must be set. Got {secret_name!r}.")
    if not destination_path:
        raise kopf.PermanentError(f"Destination path must be set. Got {destination_path!r}.")
    if not endpoint_url:
        raise kopf.PermanentError(f"Endpoint URL must be set. Got {endpoint_url!r}.")

    return {
        "apiVersion": "barmancloud.cnpg.io/v1",
        "kind": "ObjectStore",
        "metadata": {
            "name": name,
            "namespace": namespace,
        },
        "spec": {
            "configuration": {
                "destinationPath": destination_path,
                "endpointURL": endpoint_url,
                "s3Credentials": {
                    "accessKeyId": {
                        "name": secret_name,
                        "key": "ACCESS_KEY_ID",
                    },
                    "secretAccessKey": {
                        "name": secret_name,
                        "key": "SECRET_ACCESS_KEY",
                    },
                },
                "wal": {"compression": "gzip", "maxParallel": 4},
            },
        },
    }
