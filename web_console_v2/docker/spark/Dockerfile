FROM bitnami/spark:3-debian-10
LABEL Wang Sen <wangsen.0914@bytedance.com>

USER root
RUN apt update && apt install -y maven default-jdk git \
    && apt clean && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/tensorflow/ecosystem.git /opt/ecosystem
ENV ROOT_DIR /opt/ecosystem
ENV SPARK_HOME /opt/bitnami/spark/

RUN cd ${ROOT_DIR}/hadoop && mvn clean install && cp target/tensorflow-hadoop-1.10.0.jar ${SPARK_HOME}/jars/ \
    && cd ${ROOT_DIR}/spark/spark-tensorflow-connector && mvn clean install && cp target/spark-tensorflow-connector_2.12-1.11.0.jar ${SPARK_HOME}/jars/ \
    && rm -rf /opt/ecosystem
