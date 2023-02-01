import { separateLng } from 'i18n/helpers';

const users = {
  no_result: { zh: '暂无用户', en: 'No user yet' },
  yourself: { zh: '本账号' },

  btn_create_user: { zh: '创建用户', en: 'Create User' },
  btn_submit: { zh: '提交', en: 'Submit' },
  btn_delete_user: { zh: '删除用户', en: 'Delete User' },

  col_id: { zh: 'ID', en: 'ID' },
  col_username: { zh: '用户名', en: 'User Name' },
  col_password: { zh: '密码', en: 'Password' },
  col_role: { zh: '角色', en: 'Role' },
  col_name: { zh: '显示名', en: 'Display Name' },
  col_email: { zh: '邮箱', en: 'Email' },
  col_ops: { zh: '操作', en: 'Operations' },

  role_admin: { zh: '管理员' },
  role_user: { zh: '普通用户' },

  msg_delete_done: { zh: '删除成功', en: 'Delete Done' },

  title_user_create: { zh: '创建用户', en: 'Create User' },
  title_user_edit: { zh: '编辑用户', en: 'Edit User' },

  placeholder_name_searchbox: { zh: '输入关键词搜索用户', en: 'Search by name' },
  placeholder_username: { zh: '请输入用户名' },
  placeholder_password: { zh: '请输入登陆密码' },
  placeholder_name: { zh: '请输入用户昵称' },
  placeholder_email: { zh: '请输入用户邮箱' },

  placeholder_password_message: {
    zh: '至少包含一个字母、一个数字、一个特殊字符，且长度在8到20之间',
  },

  message_modify_success: { zh: '修改成功' },
  message_del_user_title: { zh: '确认删除该用户吗？' },
  message_del_user_content: { zh: '删除后，该用户将无法操作，请谨慎删除' },
  message_can_not_del_current_user: { zh: '不能删除自己的账号' },
};

export default separateLng(users);
