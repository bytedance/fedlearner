export PYTHONPATH=$PYTHONPATH:"../../"
export FLASK_APP=app_b:app
export FLASK_ENV=development
flask create-db
export K8S_CONFIG_PATH=$1
export FEDLEARNER_WEBCONSOLE_POLLING_INTERVAL=1
export SQLALCHEMY_DATABASE_URI="sqlite:///app_b.db"
export FEATURE_MODEL_WORKFLOW_HOOK=True
export FEATURE_MODEL_K8S_HOOK=True
flask run --host=0.0.0.0 --no-reload --eager-loading -p 9002
