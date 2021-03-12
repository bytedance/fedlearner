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
    upload: upload.zh,
    term: term.zh,
    error: error.zh,
    login: login.zh,
    menu: menu.zh,
    project: project.zh,
    app: app.zh,
    workflow: workflow.zh,
    dataset: dataset.zh,
    settings: settings.zh,

    all: '全部',
    terms: '服务协议',
    privacy: '隐私条款',
    more: '更多',
    confirm: '确认',
    submit: '确认',
    cancel: '取消',
    close: '关闭',
    delete: '删除',
    reset: '重置',
    previous_step: '上一步',
    next_step: '下一步',
    operation: '操作',
    certificate: '证书',
    click_to_retry: '点此重试',
    creator: '创建者',
    created_at: '创建时间',
    yes: '是',
    no: '否',
    pls_try_again_later: '请稍后重试',
  },
};

export default messages;
