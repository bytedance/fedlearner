source ./env_checker.sh

OOO=111
xxx=$(normalize_env_to_args "--xxx" $OOO)
echo $xxx
