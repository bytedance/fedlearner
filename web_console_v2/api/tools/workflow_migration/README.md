# 站内执行
```
export PRE_START_HOOK=hook:before_app_start
FLASK_APP=command:app flask migrate-workflow-completed-failed-state
```

# 站外执行
```
FLASK_APP=command:app flask migrate-workflow-completed-failed-state
```