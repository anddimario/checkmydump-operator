IMAGE_TAG ?= "latest"
DEPLOYMENT_FILE ?= "./operator/manifests/deployment.yaml"

# setup kind: add storage class, cert manager etc
.PHONY: setup-kind
setup-kind:
	kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.31/deploy/local-path-storage.yaml
	kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml
	kubectl apply --server-side -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.26/releases/cnpg-1.26.0.yaml
	kubectl apply -f https://github.com/cloudnative-pg/plugin-barman-cloud/releases/download/v0.5.0/manifest.yaml

# awk use $$ for escaping
.PHONY: start-dev
start-dev:
	docker ps -a | grep checkmydump | awk '{print $$1}' | xargs docker restart

.PHONY: stop-dev
stop-dev:
	docker ps -a | grep checkmydump | awk '{print $$1}' | xargs docker stop

.PHONY: run-dev
run-dev:
	cd operator && uv run kopf run main.py

.PHONY: push
push:
	cd operator && uv pip freeze > requirements.txt
	yq e ".spec.template.spec.containers[0].image = \"$(REPOSITORY):$(IMAGE_TAG)\"" -i $(DEPLOYMENT_FILE)
	docker build -t $(REPOSITORY):$(IMAGE_TAG) operator/
	docker push $(REPOSITORY):$(IMAGE_TAG)

.PHONY: load-kind
load-kind:
	kind load docker-image $(REPOSITORY):$(IMAGE_TAG) --name checkmydump

.PHONY: deploy-crd
deploy-crd:
	kubectl apply -f ./operator/manifests/namespace.yaml
	kubectl apply -f ./operator/manifests/crd.yaml
	kubectl apply -f ./operator/manifests/rbac.yaml

.PHONY: deploy
deploy: deploy-crd
	kubectl apply -f $(DEPLOYMENT_FILE)

.PHONY: deploy-local
deploy-local: load-kind deploy

.PHONY: cleanup-crd
cleanup-crd:
	kubectl delete -f ./operator/manifests/crd.yaml
	kubectl delete -f ./operator/manifests/rbac.yaml
	kubectl delete -f ./operator/manifests/namespace.yaml

.PHONY: cleanup-others
cleanup-others:
	kubectl delete -f $(DEPLOYMENT_FILE)

.PHONY: cleanup
cleanup: cleanup-others cleanup-crd
