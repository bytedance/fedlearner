## Google Python Style Guide

Basically we follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).

### Single-quote VS Double-quote
We use single-quote for string literals, for example:
```python
# Good
x = 'hello world'
# Bad
y = "abcbcbc"
```

### String formatting
We use f-strings or str.format to format strings, for example:
```python
# Good
x = f'hello {name}'
y = 'hello {}'.format(name)
# Bad
z = 'abc, %s' % name
```

f-strings makes our code more readable and easier to maintain, new code
should use this way to format strings.
