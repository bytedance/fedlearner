FROM registry.cn-beijing.aliyuncs.com/fedlearner/spark-py:v3.0.0
LABEL maintainers="Wang Sen <wangsen.0914@bytedance.com>, Runyu Yu<yurunyu@bytedance.com>"

USER root
ARG DEBIAN_FRONTEND=noninteractive
RUN mkdir -p /usr/share/man/man1/ && apt update && apt install -y software-properties-common \
     && apt-add-repository 'deb http://security.debian.org/debian-security stretch/updates main' \
     && apt update && apt install -y maven openjdk-8-jdk git \
     && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/tensorflow/ecosystem.git /opt/ecosystem

ENV ROOT_DIR /opt/ecosystem
ENV SPARK_HOME /opt/spark
ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
ENV PATH ${JAVA_HOME}/bin:${PATH}
ENV PYSPARK_PYTHON=/usr/bin/python3
ENV PYSPARK_DRIVER_PYTHON=/usr/bin/python3

# NOTE: scala version is 2.12
RUN cd ${ROOT_DIR}/hadoop && mvn clean install -DskipTests && cp target/tensorflow-hadoop-1.10.0.jar ${SPARK_HOME}/jars/
RUN cd ${ROOT_DIR}/spark/spark-tensorflow-connector && mvn clean install -DskipTests && cp target/spark-tensorflow-connector_2.12-1.11.0.jar ${SPARK_HOME}/jars/ \
    && rm -rf /opt/ecosystem

COPY ./requirements.txt /opt/env/requirements.txt
RUN pip3 install -U pip -i https://pypi.doubanio.com/simple \
    && /usr/bin/python3 -m pip install -r /opt/env/requirements.txt -i https://pypi.doubanio.com/simple
