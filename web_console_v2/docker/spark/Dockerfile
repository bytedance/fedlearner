FROM bitnami/spark:3-debian-10
LABEL Wang Sen <wangsen.0914@bytedance.com>

USER root

RUN apt update && apt install -y maven git \
     && apt-get clean && rm -rf "/var/lib/apt/lists/*"

ENV SPARK_HOME /opt/bitnami/spark/

RUN mvn dependency:get -Dartifact=org.tensorflow:tensorflow-hadoop:1.11.0 -Ddest=${SPARK_HOME}/jars/ \
    && mvn dependency:get -Dartifact=org.tensorflow:spark-tensorflow-connector_2.11:1.11.0 -Ddest=${SPARK_HOME}/jars/
    
COPY ./requirements.txt /opt/env/requirements.txt
RUN pip3 install -r /opt/env/requirements.txt -i https://pypi.doubanio.com/simple
