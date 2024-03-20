export PYTHONPATH=$PYTHONPATH:"../../"
export FLASK_APP=app_a:app
export FLASK_ENV=development
flask create-db
export K8S_CONFIG_PATH=$1
export FEDLEARNER_WEBCONSOLE_POLLING_INTERVAL=10
export SQLALCHEMY_DATABASE_URI="sqlite:///app_a.db"
export FEATURE_MODEL_WORKFLOW_HOOK=True
export FEATURE_MODEL_K8S_HOOK=True
export ES_READ_HOST=172.21.8.76 # aliyun-demo1 fedlearner-stack-elasticsearch-client
flask run --host=0.0.0.0 --no-reload --eager-loading -p 9001
