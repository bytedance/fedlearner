# PP Lite Client Archiver

This is a packaging tool for PP Lite - Client. Whenever you need to send your client a copy of our inspiring PP Lite, use me.

## How to Make an Archive?

### 1. Configuration

In order to make a zip file for your client, you have to prepare a configuration file in YAML.

Save it somewhere that you know.

### 2. Make Zip File with Bazel

Using Bazel, you can make your zip file blazing fast:

```bash
# --run_under option makes relative path usable
bazelisk run --run_under="cd $PWD && " //pp_lite/deploy:archiver -- -c <path_to_the_yaml_config> -o <parent_directory_of_the_output_zip_file> [-f <zip/tar>]
```

## How to Use the Archive?

Using the archive is as simple as eating an apple:

```bash
# Choose according to your format choice
unzip pp_lite_client.zip
# OR
tar xf pp_lite_client.tar

cd pp_lite
# You may find UUID in [LIGHT_CLIENT_PSI]-[more information]-[Click and check the workflow]
bash start.sh <UUID> <ABSOLUTE_INPUT_DIR>
```

You can modify this bootstrap script for sure, and so is the `.env` file, but **make sure you know what you are doing**.
