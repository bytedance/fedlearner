FROM python:3.6

RUN apt-get update && apt install -y curl
# For nodejs PA
RUN curl -sL https://deb.nodesource.com/setup_14.x | bash
# Install dependencies
RUN apt-get install -y \
        make \
		nodejs \
        nginx \
        supervisor

WORKDIR /app
# Copies all source code
COPY . .

## Builds frontend
#WORKDIR /app/client
#RUN npm ci
#RUN npm run build

# Builds backend
WORKDIR /app/api
RUN pip3 -V
RUN pip3 install -r requirements.txt
RUN make protobuf

# Nginx configuration
RUN echo "daemon off;" >> /etc/nginx/nginx.conf
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/nginx.conf

# Supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Port for webconsole http server
EXPOSE 1989
# Port for webconsole gRPC server
# This should not be exposed in PROD
EXPOSE 1990

CMD /usr/bin/supervisord
