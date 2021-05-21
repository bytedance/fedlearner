FROM registry.cn-beijing.aliyuncs.com/fedlearner/spark-py:v3.0.0
LABEL maintainer="fedlearner <fedlearner@bytedance.com>"

USER root
RUN echo "deb https://mirrors.ustc.edu.cn/debian/ buster main contrib non-free" > /etc/apt/sources.list
RUN echo "deb https://mirrors.ustc.edu.cn/debian/ buster-updates main contrib non-free" >> /etc/apt/sources.list
RUN echo "deb https://mirrors.ustc.edu.cn/debian/ buster-backports main contrib non-free" >> /etc/apt/sources.list
RUN echo "deb https://mirrors.ustc.edu.cn/debian-security/ buster/updates main contrib non-free" >> /etc/apt/sources.list
RUN echo "deb-src https://mirrors.ustc.edu.cn/debian/ buster main contrib non-free" >> /etc/apt/sources.list
RUN echo "deb-src https://mirrors.ustc.edu.cn/debian/ buster-updates main contrib non-free" >> /etc/apt/sources.list
RUN echo "deb-src https://mirrors.ustc.edu.cn/debian/ buster-backports main contrib non-free" >> /etc/apt/sources.list
RUN echo "deb-src https://mirrors.ustc.edu.cn/debian-security/ buster/updates main contrib non-free" >> /etc/apt/sources.list

RUN mkdir -p /usr/share/man/man1/ && apt update && apt install -y software-properties-common \
     && apt-add-repository 'deb http://security.debian.org/debian-security stretch/updates main' \
     && apt update && apt install -y maven openjdk-8-jdk git \
     && apt-get clean && rm -rf /var/lib/apt/lists/*

# Configure PIP
RUN pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple \
    && pip3 config set global.trusted-host https://mirrors.aliyun.com/pypi/simple \
    && pip3 config set global.extra-index-url https://mirrors.aliyun.com/pypi/simple \
    && pip3 --no-cache-dir install --upgrade setuptools pip
RUN pip3 install tensorflow==1.15.3 cityhash

ENV ROOT_DIR /opt/ecosystem
ENV SPARK_HOME /opt/spark
ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
ENV PATH ${JAVA_HOME}/bin:${PATH}
ENV PYSPARK_PYTHON=/usr/bin/python3
ENV PYSPARK_DRIVER_PYTHON=/usr/bin/python3

RUN git clone https://github.com/tensorflow/ecosystem.git /opt/ecosystem

RUN mkdir /root/.m2
COPY docker/maven/settings.xml /root/.m2

RUN cd ${ROOT_DIR}/hadoop && mvn versions:set -DnewVersion=1.15.0 && mvn clean install && cp target/tensorflow-hadoop-1.15.0.jar ${SPARK_HOME}/jars/ \
    && cd ${ROOT_DIR}/spark/spark-tensorflow-connector && mvn versions:set -DnewVersion=1.15.0 && mvn clean install  \
    && cp target/spark-tensorflow-connector_2.12-1.15.0.jar ${SPARK_HOME}/jars/ \
    && rm -rf /opt/ecosystem
