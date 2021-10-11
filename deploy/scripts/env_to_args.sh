#!/bin/bash

normalize_env_to_args() {
  if [ -z "$2" ]
  then
      echo ""
  else
      echo "$1=$2"
  fi
  return 0
}


pull_code() {
  cwd=$PWD
  cd $2
  if [[ $1 == "hdfs://"* ]]; then
      ${HADOOP_HOME}/bin/hadoop fs -copyToLocal $1 code.tar.gz
  elif [[ $1 == "http://"* || $1 == "https://"* ]]; then
      wget $1 -O code.tar.gz
  elif [[ $1 == "oss://"* ]]; then
      python -c "import tensorflow as tf; import tensorflow_io; open('code.tar.gz', 'wb').write(tf.io.gfile.GFile('$1', 'rb').read())"
  elif [[ $1 == "base64://"* ]]; then
      python -c "import base64; f = open('code.tar.gz', 'wb'); f.write(base64.b64decode('$1'[9:])); f.close()"
  else
      cp $1 code.tar.gz
  fi
  tar -zxvf code.tar.gz
  cd $cwd
}

push_file() {
  filename=`basename $1`
  target_path=$2/${filename}
  if [[ $2 == "hdfs://"* ]]; then
      ${HADOOP_HOME}/bin/hadoop fs -mkdir -p $2
      ${HADOOP_HOME}/bin/hadoop fs -put -f $1 $target_path
  elif [[ $2 == "oss://"* ]]; then
      python -c "import tensorflow as tf; import tensorflow_io; tf.io.gfile.makedirs('$2'); open('${target_path}', 'wb').write(tf.io.gfile.GFile('$1', 'rb').read())"
  else
      mkdir -p $2
      cp $1 $target_path
  fi
}
