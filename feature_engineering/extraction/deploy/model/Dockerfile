FROM tensorflow/serving:2.3.0

COPY . /

EXPOSE 8500

ENTRYPOINT ["/usr/bin/tf_serving_entrypoint.sh"]