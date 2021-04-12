## Best Practices

### Enums in DB
We recommend to use integers/strings in DB to represent enums, as we are using
flask-migrate, which needs us to upgrade the migration files once schema gets
updated (inefficiently). Integers/strings makes us easy to extend the enums,
the disadvantage is we should take care of data migrations if enum is deleted.

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
