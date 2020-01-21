.PHONY: docker-build

docker-build:
	docker build -t ${IMG} .

deploy:
	kubectl apply -f manifest
