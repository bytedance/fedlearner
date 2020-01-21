ifneq ("$(wildcard ./config.mk)","")
	include config.mk
else
	include config.mk.template
endif

.PHONY: protobuf lint test

ci:
	bash ci/ci_test.sh

protobuf:
	python -m grpc_tools.protoc -I protocols -I$(TF_PATH) \
		--python_out=. \
		--grpc_python_out=. \
		protocols/fedlearner/common/*.proto

lint:
	pylint --rcfile ci/pylintrc --ignore protobuf fedlearner 

test:
	python test/test_bridge.py
	python test/test_data_block_loader.py
	python test/test_train_master.py
	python test/test_etcd_client.py

docker-build:
	docker build . -t ${IMG}

docker-push: 
	docker push ${IMG}

