ifneq ("$(wildcard ./config.mk)","")
	include config.mk
else
	include config.mk.template
endif

.PHONY: protobuf lint test unit-test integration-test test

ci:
	bash ci/ci_test.sh

op:
	bash cc/build.sh || echo "WARN: make custom tf op failed!"

protobuf:
	python -m grpc_tools.protoc -I protocols -I$(TF_PATH) \
		--python_out=. \
		--grpc_python_out=. \
		protocols/fedlearner/common/*.proto

	python -m grpc_tools.protoc -I protocols -I$(TF_PATH) \
		--python_out=. \
		--grpc_python_out=. \
		protocols/fedlearner/channel/*.proto

lint:
#	pylint --rcfile ci/pylintrc fedlearner/trainer

UNIT_TEST_SCRIPTS := test/trainer_master/test_follower_tm.py \
                     test/trainer/test_data_visitor.py \
                     test/trainer/test_bridge.py
UNIT_TESTS := $(UNIT_TEST_SCRIPTS:%.py=%.phony)

test/%.phony: test/%.py
	python $^

unit-test: $(UNIT_TESTS)

integration-test:
	bash integration_tests.sh

test: unit-test

docker-build:
	docker build . -t ${IMG}

docker-push: 
	docker push ${IMG}
