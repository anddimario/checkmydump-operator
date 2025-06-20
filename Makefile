IMAGE_TAG ?= "latest"
DEPLOYMENT_FILE ?= "./operator/manifests/deployment.yaml"

# awk use $$ for escaping
.PHONY: dev
dev:
	docker ps -a | grep checkmydump | awk '{print $$1}' | xargs docker restart

.PHONY: stop-dev
stop-dev:
	docker ps -a | grep checkmydump | awk '{print $$1}' | xargs docker stop

.PHONY: push
push:
	cd operator && uv pip freeze > requirements.txt
	yq e ".spec.template.spec.containers[0].image = \"$(REPOSITORY):$(IMAGE_TAG)\"" -i $(DEPLOYMENT_FILE)
	docker build -t $(REPOSITORY):$(IMAGE_TAG) operator/
	docker push $(REPOSITORY):$(IMAGE_TAG)

.PHONY: load-kind
load-kind:
	kind load docker-image $(REPOSITORY):$(IMAGE_TAG) --name checkmydump

.PHONY: deploy
deploy:
	kubectl apply -f ./operator/manifests/namespace.yaml
	kubectl apply -f ./operator/manifests/crd.yaml
	kubectl apply -f ./operator/manifests/rbac.yaml
	kubectl apply -f $(DEPLOYMENT_FILE)

.PHONY: deploy-local
deploy-local: load-kind deploy

.PHONY: cleanup
cleanup:
	kubectl delete -f $(DEPLOYMENT_FILE)
	kubectl delete -f ./operator/manifests/crd.yaml
	kubectl delete -f ./operator/manifests/rbac.yaml
	kubectl delete -f ./operator/manifests/namespace.yaml
