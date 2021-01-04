import project from './modules/project'
import workflow from './modules/workflow'
import login from './modules/login'
import menu from './modules/menu'
import error from './modules/error'
import upload from './modules/upload'
import term from './modules/term'

const messages = {
  translation: {
    upload: upload.en,
    term: term.en,
    error: error.en,
    login: login.en,
    menu: menu.en,
    project: project.en,
    workflow: workflow.en,

    terms: 'Terms of Services',
    privacy: 'Privacy Protocol',
    more: 'More',
    submit: 'OK',
    cancel: 'Cancel',
    operation: 'Operation',
  },
}

export default messages
