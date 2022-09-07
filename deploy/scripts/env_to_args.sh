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
      ${HADOOP_HOME}/bin/hadoop fs -copyToLocal $1 pulled_file
  elif [[ $1 == "http://"* || $1 == "https://"* ]]; then
      wget $1 -O pulled_file
  elif [[ $1 == "oss://"* ]]; then
      python -c "import tensorflow as tf; import tensorflow_io; open('pulled_file', 'wb').write(tf.io.gfile.GFile('$1', 'rb').read())"
  elif [[ $1 == "base64://"* ]]; then
      python -c "import base64; f = open('pulled_file', 'wb'); f.write(base64.b64decode('$1'[9:])); f.close()"
  elif [[ $1 == "file://"* ]]; then
      path=$1
      pure_path=${path#file://}
      cp -r $pure_path pulled_file
  else
      cp -r $1 pulled_file
  fi

  if [[ -d pulled_file ]]; then
    mv pulled_file/* .
    rm -r pulled_file
  else
    tar -zxvf pulled_file
  cd $cwd
  fi
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
