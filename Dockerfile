FROM python:2.7

WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt . 
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . /app
RUN make protobuf

CMD []
