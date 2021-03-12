import project from './modules/project';
import workflow from './modules/workflow';
import login from './modules/login';
import menu from './modules/menu';
import error from './modules/error';
import upload from './modules/upload';
import term from './modules/term';
import app from './modules/app';
import dataset from './modules/dataset';
import settings from './modules/settings';

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
    dataset: dataset.en,
    settings: settings.en,

    all: 'All',
    terms: 'Terms of Services',
    privacy: 'Privacy Protocol',
    more: 'More',
    confirm: 'OK',
    submit: 'OK',
    cancel: 'Cancel',
    close: 'Close',
    delete: 'Delete',
    reset: 'Reset',
    operation: 'Operation',
    previous_step: 'previous step',
    next_step: 'Next step',
    certificate: 'Certificate',
    click_to_retry: 'Click to retry',
    yes: 'Yes',
    no: 'No',
    pls_try_again_later: 'Please try again later',
  },
};

export default messages;
