Restore and check your CloudNativePG backup on Kubernetes based on a schedule

> ⚠️ **Warning**
> This project is not tested in production environment and at this stage is only for educational purpose.

## HOW it works

### Requirements

- CloudNativePG, cert-manager and barman plugin (with kind you can use the task `setup-kind` in the `Makefile`)
- A bucket setup and credentials used to store the backup

### Create a cloudnative-pg cluster

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: cluster-example
spec:
  instances: 1
  plugins:
  - name: barman-cloud.cloudnative-pg.io
    isWALArchiver: true
    parameters:
      barmanObjectName: s3-store

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
apiVersion: barmancloud.cnpg.io/v1
kind: ObjectStore
metadata:
  name: s3-store
spec:
  configuration:
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

---
# it seems that a full backup is needed to create the base in the s3
apiVersion: postgresql.cnpg.io/v1
kind: Backup
metadata:
  name: backup-cluster-example
spec:
  cluster:
    name: cluster-example
  method: plugin
  pluginConfiguration:
    name: barman-cloud.cloudnative-pg.io
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

> NOTE
> Queries are optional

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
---
apiVersion: checkmydump.com/v1alpha1
kind: CheckMyDumpQuery
metadata:
  name: checkmydump-test-query1
  namespace: checkmydump
  labels:
    checkmydumps: checkmydump-test
spec:
  query: ...
  expectedResult: "..."
---
apiVersion: checkmydump.com/v1alpha1
kind: CheckMyDumpQuery
metadata:
  name: checkmydump-test-query2
  namespace: checkmydump
  labels:
    checkmydumps: checkmydump-test
spec:
  query: ...
```
