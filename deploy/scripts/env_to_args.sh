#!/bin/bash

normalize_env_to_args() {
  if [ -z "$2" ]
  then
      echo ""
  else
      echo "$1=\"$2\""
  fi
  return 0
}
