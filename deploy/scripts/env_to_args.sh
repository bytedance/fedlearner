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
<<<<<<< HEAD
      python -c "import tensorflow.compat.v1 as tf; import tensorflow_io; open('pulled_file', 'wb').write(tf.io.gfile.GFile('$1', 'rb').read())"
=======
<<<<<<< HEAD
      python -c "import tensorflow.compat.v1 as tf; import tensorflow_io; open('code.tar.gz', 'wb').write(tf.io.gfile.GFile('$1', 'rb').read())"
=======
      python -c "import tensorflow as tf; import tensorflow_io; open('pulled_file', 'wb').write(tf.io.gfile.GFile('$1', 'rb').read())"
>>>>>>> 21d2ae40 (feat(code): add dictionary support for code_key (#931))
>>>>>>> 81f0ed0c (feat(code): add dictionary support for code_key (#931))
  elif [[ $1 == "base64://"* ]]; then
      python -c "import base64; f = open('pulled_file', 'wb'); f.write(base64.b64decode('$1'[9:])); f.close()"
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
