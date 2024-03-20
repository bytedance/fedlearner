import i18n from 'i18n';

const PASSWORD_REGX = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[!@#$%^&*()_=+|{};:'",<.>/?~])[A-Za-z\d!@#$%^&*()_=+|{};:'",<.>/?~]{8,20}$/i;
export async function validatePassword(
  value: string,
  options: { message: string } = { message: i18n.t('users.placeholder_password_message') },
) {
  if (PASSWORD_REGX.test(value)) {
    return true;
  }

  throw new Error(options.message);
}
