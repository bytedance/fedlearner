import project from './modules/project'
import workflow from './modules/workflow'
import login from './modules/login'
import menu from './modules/menu'
import error from './modules/error'
import upload from './modules/upload'
import term from './modules/term'

const messages = {
  translation: {
    upload: upload.zh,
    term: term.zh,
    error: error.zh,
    login: login.zh,
    menu: menu.zh,
    project: project.zh,
    workflow: workflow.zh,

    all: '全部',
    terms: '服务协议',
    privacy: '隐私条款',
    more: '更多',
    submit: '确认',
    cancel: '取消',
    previous_step: '上一步',
    next_step: '下一步',
    operation: '操作',
    certificate: '证书',
    click_to_retry: '点此重试',
  },
}

export default messages
