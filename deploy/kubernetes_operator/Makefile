.PHONY: docker-build

docker-build:
	docker build -t ${IMG} .

docker-push:
	docker push ${IMG}

deploy:
	kubectl apply -f manifest/controller.yaml
