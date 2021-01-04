import PubSub from 'pubsub-js'

export const workflowPubsub = PubSub

const WORKFLOW_CHANNELS = {
  create_new_tpl: 'workflow.create_new_tpl',
  go_config_step: 'workflow.go_config_step',
  tpl_create_succeed: 'workflow.tpl_create_succeed',
}

export default WORKFLOW_CHANNELS
