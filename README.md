Check your CloudNativePG backup on Kubernetes based on a schedule

> ⚠️ **Warning**
> This project is not tested in production environment.

## HOW it works

### Requirements

- CloudNativePG
- A bucket setup and credentials used to store the backup

### Create a cloudnative-pg cluster

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: cluster-example
spec:
  instances: 1

  backup:
    barmanObjectStore:
      destinationPath: EDIT_HERE
      endpointURL: EDIT_HERE
      s3Credentials:
        accessKeyId:
          name: bucket-cred
          key: ACCESS_KEY_ID
        secretAccessKey:
          name: bucket-cred
          key: SECRET_ACCESS_KEY
      wal:
        compression: gzip
        maxParallel: 4
      data:
        compression: gzip
        # immediateUpload: true
    retentionPolicy: "7d"  # keep backups for 7 days


  storage:
    size: 1Gi

---
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  name: bucket-cred
stringData:
  ACCESS_KEY_ID: EDIT_HERE
  SECRET_ACCESS_KEY: EDIT_HERE


---
# it seems that a full backup is needed to create the base in the s3
apiVersion: postgresql.cnpg.io/v1
kind: Backup
metadata:
  name: backup-cluster-example
spec:
  cluster:
    name: cluster-example
```

### Add the operator

```bash
make push IMAGE_TAG=v0.0.1 REPOSITORY=myorg/checkmydump
make deploy
```

### Create the secret with bucket credentials in the `checkmydump` namespace

```yaml
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  name: bucket-cred
  namespace: checkmydump
stringData:
  ACCESS_KEY_ID: EDIT_HERE
  SECRET_ACCESS_KEY: EDIT_HERE
```

### Create the resource

```yaml
apiVersion: checkmydump.com/v1alpha1
kind: CheckMyDump
metadata:
  name: checkmydump-test
  namespace: checkmydump
spec:
  schedule: "0 3 * * *"
  size: 1G
  sourceClusterName: cluster-example
  secretName: ...
  destinationPath: "..."
  endpointURL: "..."
```
