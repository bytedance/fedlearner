import axios, { AxiosInstance } from 'axios'

declare module 'axios' {
  interface AxiosRequestConfig {
    singleton?: symbol
  }
}

export const HOSTNAME = '/api'

let request: AxiosInstance

if (process.env.NODE_ENV === 'development') {
  // NOTE: DEAD CODE HERE
  // will be removed during prod building
  request = axios.create({ adapter: require('./mockAdapter').default, baseURL: HOSTNAME })
} else {
  request = axios.create({
    baseURL: HOSTNAME,
  })
}

const SingletonCollection = new Map()

/** Singleton control interceptor */
request.interceptors.request.use((config) => {
  if (config.singleton) {
    const oldSource = SingletonCollection.get(config.singleton)
    if (oldSource) {
      oldSource.cancel()
    }
    const source = axios.CancelToken.source()
    config.cancelToken = source.token
    SingletonCollection.set(config.singleton, source)
  }

  return config
})

request.interceptors.response.use(
  (response) => {
    if (response.config?.singleton) {
      SingletonCollection.delete(response.config.singleton)
    }
    return response
  },
  (error) => {
    if (error?.config?.singleton) {
      SingletonCollection.delete(error.config.singleton)
    }
    return Promise.reject(error)
  },
)

export default request
