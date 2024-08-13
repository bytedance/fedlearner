FROM python:3.6.8

RUN apt-get update && \
    apt install -y curl && \
    # For nodejs PA
    curl -sL https://deb.nodesource.com/setup_14.x | bash && \
    # For krb5-user installation
    export DEBIAN_FRONTEND=noninteractive && \
    # Install dependencies
    apt-get install -y make nodejs nginx krb5-user cron && \
    apt-get clean

WORKDIR /app
# Copies all source code
COPY . .

# Builds frontend
WORKDIR /app/client
RUN npx pnpm@6.4.0 install && npx pnpm@6.4.0 build && rm -rf node_modules

# Builds backend
WORKDIR /app/api
RUN pip3 install --no-cache-dir -r requirements.txt && make protobuf

WORKDIR /app
# Nginx configuration
RUN cp nginx.conf /etc/nginx/conf.d/nginx.conf

# Port for webconsole http server
EXPOSE 1989
# Port for webconsole gRPC server
# This should not be exposed in PROD
EXPOSE 1990

ENV TZ="Asia/Shanghai"

WORKDIR /app
CMD bash run_prod.sh
