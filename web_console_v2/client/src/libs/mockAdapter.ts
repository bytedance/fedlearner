import axios, { AxiosRequestConfig } from 'axios'
import { sleep } from 'shared/helpers'

async function axiosMockAdapter(config: AxiosRequestConfig) {
  try {
    await sleep(Math.random() * 1000)

    const data = require(`../services/mocks${config.url}`).default

    // HTTP code other than 2xx, 3xx should be rejected
    if (['2', '3'].includes(data.status.toString().charAt(0))) {
      return data
    }
    return Promise.reject(data)
  } catch (error) {
    console.error('[Mock Adapter]: ', error)
  }

  return axios.defaults.adapter!(config)
}

export default axiosMockAdapter
