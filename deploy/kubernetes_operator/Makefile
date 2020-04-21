.PHONY: docker-build

docker-build:
	docker build -t ${IMG} .

docker-push:
	docker push ${IMG}

deploy:
	kubectl apply -f manifest/controller.yaml

update-codegen:
	./hack/update-codegen.sh

update-controllergen:
	controller-gen paths=${SCRIPT_ROOT}/pkg/apis/... output:dir=${SCRIPT_ROOT}/manifests  crd:trivialVersions=true

update-defaulter:
	defaulter-gen --input-dirs github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1 --go-header-file ./hack/boilerplate.go.txt

vendor:
	go mod vendor

crd:
	controller-gen paths=./pkg/apis/... output:dir=../charts/manifests  crd:trivialVersions=true
