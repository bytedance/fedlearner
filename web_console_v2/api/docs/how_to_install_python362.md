# Background:

When we use the outdated software version, the lack of upward compatibility will cause us to be unable to use higher versions of python. At this time, we need to switch and isolate the python version.

In our project environment, we need to use the version of tensorflow v1.15.0, which requires a version of python3.6.2



# How to install&use:

## 1. Get a python3.6.2 using pyenv

Firstly, we use *brew* to install *pyenv*:

```shell
brew install pyenv
pyenv -v # check pyenv version
```

then, we check the python3.6 version provide by pyenv and install the version we need:

```shell
pyenv install --list | grep 3.6
pyenv install 3.6.2
```



###### if you see error like this, 

```shell
Last 10 log lines:
./Modules/posixmodule.c:8210:15: error: implicit declaration of function 'sendfile' is invalid in C99 [-Werror,-Wimplicit-function-declaration]
ret = sendfile(in, out, offset, &sbytes, &sf, flags);
^
./Modules/posixmodule.c:10432:5: warning: code will never be executed [-Wunreachable-code]
Py_FatalError("abort() called from Python code didn't abort!");
^~~~~~~~~~~~~
1 warning and 1 error generated.
make: *** [Modules/posixmodule.o] Error 1
make: *** Waiting for unfinished jobs....
1 warning generated`
```

###### you can try to install python version using:

```shell
CFLAGS="-I$(brew --prefix openssl)/include -I$(brew --prefix bzip2)/include -I$(brew --prefix readline)/include -I$(xcrun --show-sdk-path)/usr/include" LDFLAGS="-L$(brew --prefix openssl)/lib -L$(brew --prefix readline)/lib -L$(brew --prefix zlib)/lib -L$(brew --prefix bzip2)/lib" pyenv install --patch 3.6.2 < <(curl -sSL https://github.com/python/cpython/commit/8ea6353.patch\?full_index\=1)
```



Check all the available python versions in pyenv to make sure your python3.6.2 installed successfully:

```shell
pyenv versions
```



## 2. create your own python3.6.2 virtualenv:

When using different python versions, I strongly recommend you to create a python virtual environment to isolate the python packages between different versions.

the python3.6.2 path installed by *pyenv* is ~/.pyenv/versions/3.6.2/bin/python3.6

create/manage/use your python3.6.2 virtualenv by *virtualenvwrapper*:

```shell
mkvirtualenv --python=/users/bytedance/.pyenv/versions/3.6.2/bin/python3.6 $ENV_NAME
workon $ENV_NAME
```

or just using *venv*, or you can just using the virtualenv created by *pycharm*



***note***: please **DO NOT** directly install packages based on python3.6.2 on your real env