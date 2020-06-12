# Fedlearner™ Platform

the machine learning platform of [Fedlearner][fedlearner].

## Prerequisites

- Concepts
  * api: the website REST API
  * middlewares: the middlewares of REST API
  * pages: the website pages
  * scheduler: the training scheduler of platform
- Environment
  * only use Maintenance LTS or Active LTS version of [Node.js][node]
  * always lock the version of dependencies
  * use `package-lock.json` to manage dependencies
  * always setup dependencies with `npm ci`
  * remember to update `package-lock.json` for new dependencies by `npm i`
- Contribution
  * use [Conventional Commits][conventionalcommits] for commit message
  * code coverage **must be** greater than `80%`

## Development

```
npm ci
npm run dev
```

then open site at [http://127.0.0.1:1989](http://127.0.0.1:1989).

## Deployment

to be done

## Testing

make sure you have installed [Docker][docker] and [Minikube][minikube],
and start Kubernetes cluster first:

```
minikube start
```

```
npm run test
```

for testing with coverage report:

```
npm run cov
```

------------------------------------------------------------------------------
[conventionalcommits]: https://www.conventionalcommits.org/en/v1.0.0/#summary
[docker]: https://www.docker.com/get-started
[fedlearner]: https://github.com/bytedance/fedlearner
[koa]: https://koajs.com
[minikube]: https://minikube.sigs.k8s.io
[next]: https://nextjs.org/docs
[node]: https://nodejs.org/en/about/releases
[nvm]: https://github.com/nvm-sh/nvm
[sequelize]: https://sequelize.org
[zeit_ui]: https://react.zeit-ui.co/zh-cn/components/text
