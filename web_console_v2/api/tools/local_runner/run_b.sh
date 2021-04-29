export PYTHONPATH=$PYTHONPATH:"../../"
export FLASK_APP=app_b:app
export FLASK_ENV=development
flask create-db
export K8S_CONFIG_PATH=$0
flask run --host=0.0.0.0 -p 8000
