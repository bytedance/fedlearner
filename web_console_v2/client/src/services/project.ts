import { AxiosPromise } from 'axios'
import request from 'libs/request'

export function fetchExampleWorkflowTemplate() {
  return request('/v2/projects')
}
