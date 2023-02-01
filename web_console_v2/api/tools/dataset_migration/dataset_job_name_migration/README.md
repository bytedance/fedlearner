# 站内执行
```
export PRE_START_HOOK=hook:before_app_start
FLASK_APP=command:app flask migrate-dataset-job-name
```

# 站外执行
```
FLASK_APP=command:app flask migrate-dataset-job-name
```