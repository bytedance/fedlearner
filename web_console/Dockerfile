FROM mhart/alpine-node:12

WORKDIR /app

COPY . .

# add command below if native addons were required
# RUN apk add --no-cache make gcc g++ python

RUN npm ci

RUN npm run build

EXPOSE 1989

CMD ["node", "bootstrap.js"]
