FROM python:3.6

WORKDIR /relay

RUN mkdir -p /relay/core /relay/serving

COPY ./core/serving_client_test.py /relay/core/
COPY serving_test /relay/serving/
COPY restful_relay.py /relay
COPY requirements.txt /relay

RUN pip3 --no-cache-dir install --upgrade pip \
    && pip3 --no-cache-dir install -r requirements.txt

ENV PYTHONPATH=/relay:$PYTHONPATH

EXPOSE 5000

RUN echo '#!/bin/bash \n\n\
    python /relay/restful_relay.py --serving_hostport=${SERVING_HOSTPORT} \
    "$@"' > /relay/relay_entrypoint.sh \
    && chmod +x /relay/relay_entrypoint.sh

ENTRYPOINT ["/relay/relay_entrypoint.sh"]
