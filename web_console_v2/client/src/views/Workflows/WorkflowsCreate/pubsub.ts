import PubSub from 'pubsub-js'

export const workflowPubsub = PubSub

const WORKFLOW_CHANNELS = {
  create_new_tpl: 'workflows.create_new_tpl',
  go_config_step: 'workflows.go_config_step',
  tpl_create_succeed: 'workflows.tpl_create_succeed',
}

export default WORKFLOW_CHANNELS
