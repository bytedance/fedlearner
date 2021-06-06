FROM python:3.7

RUN apt-get update && \
    apt install -y curl && \
    # For nodejs PA
    curl -sL https://deb.nodesource.com/setup_14.x | bash && \
    # Install dependencies
    apt-get install -y make nodejs nginx && \
    apt-get clean

WORKDIR /app
# Copies all source code
COPY . .

# Builds frontend
WORKDIR /app/client
RUN npx pnpm install && npx pnpm build && rm -rf node_modules

# Builds backend
WORKDIR /app/api
RUN pip3 install --no-cache-dir -r requirements.txt && make protobuf

# Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/nginx.conf

# Port for webconsole http server
EXPOSE 1989
# Port for webconsole gRPC server
# This should not be exposed in PROD
EXPOSE 1990

# Install vscode
RUN curl -fOL https://github.com/cdr/code-server/releases/download/v3.8.0/code-server_3.8.0_amd64.deb && \
    dpkg -i code-server_3.8.0_amd64.deb && \
    rm code-server_3.8.0_amd64.deb && \
    mkdir -p ~/.config/code-server/ && \
    echo 'bind-addr: 0.0.0.0:1992\n\
auth: password\n\
password: fedlearner\n\
cert: false\n' >> ~/.config/code-server/config.yaml

# Port for VScode
EXPOSE 1992
ENV TZ="Asia/Shanghai"

WORKDIR /app
CMD sh run_prod.sh
