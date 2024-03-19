#!/bin/bash

ROOT_DIRECTORY=$1
/bin/sh $ROOT_DIRECTORY/runtime_env.sh

python3 $ROOT_DIRECTORY/tools/dataset_importer_migration/dataset_file_migration.py