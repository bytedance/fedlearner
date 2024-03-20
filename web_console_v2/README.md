## Web console V2 is working in progress

### Docker
```shell
docker build --memory 4G --tag fedlearner_webconsole_v2 .
docker run --rm -it -p 1989:1989 -p 1990:1990 fedlearner_webconsole_v2
```
Then visiting http://localhost:1989/ for the UI.

### Style Guide

#### Git commit message guidelines

Each commit message has a special format that includes a type, a scope and a subject: `<type>(<scope>): <subject>`

**Type** must be one of the following:

* feat: A new feature
* fix: A bug fix
* docs: Documentation only changes
* refactor: A code change that neither fixes a bug nor adds a feature
* perf: A code change that improves performance
* test: Adding missing or correcting existing tests
* chore: Changes to the build process or auxiliary tools and libraries such as documentation generation

**Scope** could be anything specifying place of the commit change. For example dataset, composer, etc...You can use * when the change affects more than a single scope.

**Subject** contains succinct description of the change. If this change is related with some issue, `#issue_id` should be included. The format is like `<type>(<scope>): description #issue_id`.

