FROM python:3.6
WORKDIR /app

COPY . /app

RUN apt-get -y update \
    && apt-get -y install libgmp-dev \
    && apt-get -y install libmpfr-dev \
    && apt-get -y install libmpc-dev \
    && rm -rf /var/lib/apt/lists/* 

RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && rm -rf ~/.cache/pip

RUN make protobuf \
    && make op

ENV PYTHONPATH=/app:$PYTHONPATH

CMD []