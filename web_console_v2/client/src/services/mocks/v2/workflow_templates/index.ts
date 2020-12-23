import exampleWorkflow from './example'

export const post = {
  data: exampleWorkflow.data,
  status: 200,
}

const get = {
  data: {
    list: [exampleWorkflow.data],
  },
  status: 200,
}

export default get
