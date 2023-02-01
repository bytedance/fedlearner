## Best Practices

### Enums in DB
We recommend to use integers/strings in DB to represent enums, as we are using
flask-migrate, which needs us to upgrade the migration files once schema gets
updated (inefficiently). Integers/strings makes us easy to extend the enums,
the disadvantage is we should take care of data migrations if enum is deleted.

Natively sqlalchemy support Enum type in a column. [Ref](https://docs.sqlalchemy.org/en/14/core/type_basics.html#sqlalchemy.types.Enum)

### Index in DB
Index is not necessary if the value of column is very limited, such as enum
or boolean. Reference: https://tech.meituan.com/2014/06/30/mysql-index.html

### RESTful API
We use RESTful to organize the resources and API endpoint, briefly it thinks
everything as a resource, and HTTP verb to act on those resources. For example:
```python
# GET /api/v2/datasets to list datasets
# POST /api/v2/datasets to create a new dataset
# GET /api/v2/datasets/<:id> to get a specific dataset
# PATCH /api/v2/datasets/<:id> to update a dataset partially
# DELETE /api/v2/datasets/<:id> to delete a dataset
```
See details [here](https://en.wikipedia.org/wiki/Representational_state_transfer)

### sqlalchemy ORM declarative
* Do not use MySQL keywords as the column name, you could specify the column
  name in sqlalchemy if it makes code more readable to use keyword as the name.
* Please add comment for each column
    ```python
    comment = db.Column('cmt',
                        db.String(255),
                        key='comment',
                        comment='comment')
    ```

* Please explicitly `Index('idx_{column_name}', tbl.column)` to declare index
  in `__table_args__` of model class.
* Please explicitly `UniqueConstraint(*columns, name='uniq_{columns}')` to declare
  unique constraint in `__table_args__` of model class.
    ```python
    class WorkflowTemplate(db.Model):
      __tablename__ = 'template_v2'
      __table_args__ = (UniqueConstraint('name', name='uniq_name'),
                        Index('idx_group_alias', 'group_alias'), {
                              'comment': 'workflow template',
                        })
    ```

* Do not use foreign key, using `db.relationship('tbl_name',primaryjoin='foreign(tbl_name.column) == referenced_tbl.column')`
  to claim instead.
    ```python
    project = db.relationship('Project',
                              primaryjoin='Project.id == '
                              'foreign(Job.project_id)')
    ```

### sqlalchemy session
* Please limit the session/transaction scope as small as possible, otherwise it may not work as expected.
[Ref](https://docs.sqlalchemy.org/en/14/orm/session_basics.html#when-do-i-construct-a-session-when-do-i-commit-it-and-when-do-i-close-it)
```python
#BAD: the transaction will include the runner query, it may stale.
with db.session_scope() as session:
  init_runners = session.query(SchedulerRunner).filter_by(
    status=RunnerStatus.INIT.value).all()
  for runner in init_runners:
    # Do something with the runner
    session.commit()

#GOOD: make the transaction scope clear.
with db.session_scope() as session:
  running_runner_ids = session.query(SchedulerRunner.id).filter_by(
    status=RunnerStatus.RUNNING.value).all()
for runner_id, *_ in running_runner_ids:
  with db.session_scope() as session:
    runner = session.query(SchedulerRunner).get(runner_id)
    # Do something with the runner
    session.commit()
```

### Pagination
- Use `utils/paginate.py`, and **read the test case** as a quickstart
- All resources are **un-paginated** by default
- Append page metadata in your returned body in the following format:
```json
// your POV
{
  "data": pagination.get_items(),
  "page_meta": pagination.get_metadata()
}

// frontend POV
{
  "data": {...},
  "page_meta": {
    "current_page": 1,
    "page_size": 5,
    "total_pages": 2,
    "total_items": 7
  }
}
```
- **ALWAYS** return `page_meta`
  - If your API is called with `page=...`, then paginate for the caller; return the pagination metadata as shown above
  - If your API is called without `page=...`, then return the un-paginated data with an **empty** `page_meta` body like so:
  ```json
  {
    "data": {...},
    "page_meta": {}
  }
  ```
