# Fedlearner™ Web Console

the web console of [Fedlearner][fedlearner].

## Prerequisites

- Concepts
  * api: the website REST API
  * components: common react components used for pages
  * libs: common libs such as LRU cache and Kubenetes client
  * middlewares: common middlewares of REST API
  * models: database ORMs
  * pages: the website pages
  * public: static files
  * services: RPC caller
  * tests: test suites
  * utils: common utilities
- Environment
  * only use Maintenance LTS or Active LTS version of [Node.js][node]
  * always lock the version of dependencies
  * use `package-lock.json` to manage dependencies
  * always setup dependencies with `npm ci`
  * remember to update `package-lock.json` for new dependencies by `npm i`
  * use [MySQL][mysql] 5.6+ version (or [MariaDB][mariadb] 10.0+ version)
- Config
  * use `server.config.js` to config environment variables
  * `K8S_HOST`: the hostname of Kubernetes api server
  * `K8S_PORT`: the port of Kubernetes api server
- Contribution
  * use [Conventional Commits][conventionalcommits] for commit message
  * code coverage **must be** greater than `80%`

## Development

make sure local-hosted database was setup

```
npm ci
npm run dev
```

then open site at [http://127.0.0.1:1989](http://127.0.0.1:1989).

## Deployment

make sure [Docker][docker] and remote-hosted database were setup

```
npm run build:image
docker run --rm -it -p 1989:1989 -e DB_HOST=[database host] DB_USERNAME=[database username] DB_PASSWORD=[database password] fedlearner-web-console
```

## Testing

```
npm run test
```

for testing with coverage report:

```
npm run cov
```

------------------------------------------------------------------------------
[conventionalcommits]: https://www.conventionalcommits.org/en/v1.0.0/#summary
[docker]: https://docs.docker.com/get-docker
[fedlearner]: https://github.com/bytedance/fedlearner
[koa]: https://koajs.com
[mariadb]: https://downloads.mariadb.org
[minikube]: https://minikube.sigs.k8s.io
[mysql]: https://dev.mysql.com/downloads/mysql
[next]: https://nextjs.org/docs
[node]: https://nodejs.org/en/about/releases
[nvm]: https://github.com/nvm-sh/nvm
[sequelize]: https://sequelize.org
[zeit_ui]: https://react.zeit-ui.co/zh-cn/components/text
