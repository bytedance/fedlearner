const isProd = process.env.NODE_ENV === 'production';

module.exports = {
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint', 'prettier'],
  extends: [
    // 'plugin:@typescript-eslint/eslint-recommended',
    // 'plugin:@typescript-eslint/recommended',
    'react-app',
    // 'prettier/@typescript-eslint',
    'prettier',
  ],
  env: {
    browser: true,
    commonjs: true,
    es6: true,
    node: true,
  },
  parserOptions: {
    sourceType: 'module',
  },
  rules: {
    'no-console': isProd ? ['error', { allow: ['error'] }] : 'off',
    'no-debugger': isProd ? 'error' : 'off',
    'comma-style': ['error', 'last'],
    'react/self-closing-comp': [
      'error',
      {
        component: true,
        html: true,
      },
    ],
    '@typescript-eslint/semi': 'off',
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    'prettier/prettier': ['warn', {}, { usePrettierrc: true }],
    'prefer-const': [
      'error',
      {
        destructuring: 'any',
        ignoreReadBeforeAssign: false,
      },
    ],
  },
  overrides: [
    {
      files: ['**/tests/*.{j,t}s?(x)', '**/tests/**/*.spec.{j,t}s?(x)'],
      env: {
        jest: true,
      },
    },
  ],
};
