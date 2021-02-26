ifneq ("$(wildcard ./config.mk)","")
	include config.mk
else
	include config.mk.template
endif

.PHONY: protobuf lint test unit-test integration-test test webconsole2-test

ci:
	bash ci/ci_test.sh

op:
	bash cc/build.sh || echo "WARN: make custom tf op failed!"

protobuf:
	python -m grpc_tools.protoc -I protocols -I$(TF_PATH) \
		--python_out=. \
		--grpc_python_out=. \
		protocols/fedlearner/common/*.proto
	cd web_console_v2/api; make protobuf

lint:
	pylint --rcfile ci/pylintrc fedlearner example
	cd web_console_v2/api; make lint

UNIT_TEST_SCRIPTS := $(shell find test -type f -name "test_*.py")
UNIT_TESTS := $(UNIT_TEST_SCRIPTS:%.py=%.phony)

test/%.phony: test/%.py
	python $^

unit-test: $(UNIT_TESTS)

integration-test:
	bash integration_tests.sh

webconsole2-test:
	cd web_console_v2/api; make test

test: integration-test unit-test webconsole2-test

docker-build:
	docker build . -t ${IMG}

docker-push: 
	docker push ${IMG}

