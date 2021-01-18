import project from './modules/project';
import workflow from './modules/workflow';
import login from './modules/login';
import menu from './modules/menu';
import error from './modules/error';
import upload from './modules/upload';
import term from './modules/term';
import app from './modules/app';

const messages = {
  translation: {
    upload: upload.en,
    term: term.en,
    error: error.en,
    login: login.en,
    menu: menu.en,
    project: project.en,
    workflow: workflow.en,
    app: app.en,

    all: 'All',
    terms: 'Terms of Services',
    privacy: 'Privacy Protocol',
    more: 'More',
    submit: 'OK',
    cancel: 'Cancel',
    operation: 'Operation',
    previous_step: 'previous step',
    next_step: 'Next step',
    certificate: 'Certificate',
    click_to_retry: 'Click to retry',
  },
};

export default messages;
