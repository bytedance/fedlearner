#!/bin/bash
if grep -q "psi-ot" .env
then
  if [[ $1 == '' ||  $2 == '' ||  $3 == '' ]]
  then
    echo "[Usage]: bash $0 [param1: UUID] [param2: INPUT_DIR] [param3: NUM_WORKERS]"
    exit 1
  fi
  NUM_WORKERS=$3
  sed -i".bak" -e "s/NUM_WORKERS.*/NUM_WORKERS=${NUM_WORKERS}/" .env
else
  if [[ $1 == '' ||  $2 == '' ]]
  then
    echo "[Usage]: bash $0 [param1: UUID] [param2: INPUT_DIR]"
    exit 1
  fi
fi
UUID=$1
INPUT_DIR=$2

set -e
sed -i".bak" -e "s/SERVICE_ID.*/SERVICE_ID=${UUID}-lc-start-server-worker-0/" .env

if test -z "$(docker images | grep pp_lite)"
then
  echo "Loading image..."
  docker load -i client_image.tar
else
  echo "Image already satisfied."
fi

IMAGE_URI="$(docker images --format '{{ .Repository }}:{{ .Tag }}' | grep pp_lite | head -n 1)"
echo "Using $IMAGE_URI to proceed."

echo "Start Client..."
docker run -it --rm --env-file .env \
           -v "$PWD":/app/workdir \
           -v "${INPUT_DIR}":/app/workdir/input \
           "${IMAGE_URI}"
echo "Start Client... [DONE]"
