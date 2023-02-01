# Code for BE API

## Prerequisites

* Bazel
* MySQL 8.0
* Docker

## Get started

Starting development by using fake k8s (no actual data).

start all the processes

```bash
bazelisk run //web_console_v2/api/cmds:run_dev
```

optionally if you want to stop or restart one of the processes

```bash
bazelisk run //web_console_v2/api/cmds:supervisorctl_cli_bin -- -s unix:///tmp/supervisor.sock
```

## Develop with remote k8s cluster

```bash
# Changes configs in tools/local_runner/app_a.py or app_b.py
bash tools/local_runner/run_a.sh
bash tools/local_runner/run_b.sh
```

## Tests

### Unit tests

```bash
bazelisk test //web_console_v2/api/... --config lint
```

## Helpers

### Gets all routes

```bash
FLASK_APP=web_console_v2/api/command:app \
    APM_SERVER_ENDPOINT=/dev/null \
    bazelisk run //web_console_v2/api/cmds:flask_cli_bin -- routes
```

### Add migration files

```bash
FLASK_APP=web_console_v2/api/command:app \
    APM_SERVER_ENDPOINT=/dev/null \
    bazelisk run //web_console_v2/api/cmds:flask_cli_bin -- db migrate -m "Whats' changed" -d web_console_v2/api/migrations

# like dry-run mode, preview auto-generated SQL
FLASK_APP=web_console_v2/api/command:app \
    APM_SERVER_ENDPOINT=/dev/null \
    bazelisk run //web_console_v2/api/cmds:flask_cli_bin -- db upgrade --sql -d web_console_v2/api/migrations

# update database actually
FLASK_APP=web_console_v2/api/command:app \
    APM_SERVER_ENDPOINT=/dev/null \
    bazelisk run //web_console_v2/api/cmds:flask_cli_bin -- db upgrade -d web_console_v2/api/migrations
```

### Reset migration files

Delete migrations folder first.

```bash
FLASK_APP=web_console_v2/api/command:app \
    APM_SERVER_ENDPOINT=/dev/null \
    bazelisk run //web_console_v2/api/cmds:flask_cli_bin -- db init -d web_console_v2/api/migrations

FLASK_APP=web_console_v2/api/command:app \
    APM_SERVER_ENDPOINT=/dev/null \
    bazelisk run //web_console_v2/api/cmds:flask_cli_bin -- db migrate -m "Initial migration." -d web_console_v2/api/migrations
```

### Cleanup project

```bash
FLASK_APP=web_console_v2/api/command:app \
    APM_SERVER_ENDPOINT=/dev/null \
    bazelisk run //web_console_v2/api/cmds:flask_cli_bin -- cleanup-project <project_id>
```

## 规范 & 风格

### [Style guide](docs/style_guide.md)

### Code formatter

We use [yapf](https://github.com/google/yapf) to format our code, style is defined in `.style.yapf`.

To check the format, please run:

```bash
bazelisk test <target> --config lint
```

To fix the errors, please run:

```bash
bazelisk test <target> --config fix
```

### [gRPC](docs/grpc.md)

## 最佳实践

### [数据库相关最佳实践](docs/best_practices/db.md)

### [API层最佳实践](docs/best_practices.md)

### [客户端-服务端模型最佳实践](docs/best_practices/client_server.md)

### [多进程最佳实践](docs/best_practices/multiprocess.md)

## References

### Default date time in sqlalchemy

https://stackoverflow.com/questions/13370317/sqlalchemy-default-datetime/33532154#33532154
