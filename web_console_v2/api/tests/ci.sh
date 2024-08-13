#!/bin/bash
set -ex

# Run CLI tests
web_console_v2/api/cmds/flask_cli_bin routes

# Run migrations tests
migration_heads=$(
    web_console_v2/api/cmds/flask_cli_bin \
        db heads -d web_console_v2/api/migrations | wc -l
)
[[ $migration_heads -eq 1 ]]
