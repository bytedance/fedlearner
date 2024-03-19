export PYTHONPATH:=${PWD}:$(PYTHONPATH)

clean:
	rm -f err.out && \
	find ./ -type f \( -name "*.db" -o -name "*.log" \) -exec rm -f {} \;

protobuf:
	PATH=${PATH}:${PWD}/bin/$(shell uname) \
	python -m grpc_tools.protoc -I protocols \
		--python_out=. \
		--grpc_python_out=. \
		--mypy_out=. \
		--jsonschema_out=prefix_schema_files_with_package,disallow_additional_properties:fedlearner_webconsole/proto/jsonschemas \
		protocols/fedlearner_webconsole/proto/*.proto \
		protocols/fedlearner_webconsole/proto/**/*.proto \
		protocols/fedlearner_webconsole/proto/rpc/v2/*.proto
