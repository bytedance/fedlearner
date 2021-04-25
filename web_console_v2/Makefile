api-test:
	cd api && \
	make protobuf && \
	make lint && \
	make test

docker-spark:
	cd ./docker/spark && docker build . -t spark-tfrecord:latest