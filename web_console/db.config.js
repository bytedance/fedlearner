module.exports = {
  development: {
    database: process.env.DB_DATABASE || 'fedlearner',
    username: process.env.DB_USERNAME || 'fedlearner',
    password: process.env.DB_PASSWORD || 'fedlearner',
    host: process.env.DB_HOST || '127.0.0.1',
    port: Number(process.env.DB_PORT) || 3306,
    dialect: 'mysql',
  },
  production: {
    database: process.env.DB_DATABASE || 'fedlearner',
    username: process.env.DB_USERNAME || 'fedlearner',
    password: process.env.DB_PASSWORD || 'fedlearner',
    host: process.env.DB_HOST || '127.0.0.1',
    port: Number(process.env.DB_PORT) || 3306,
    dialect: 'mysql',
  },
  test: {
    database: process.env.DB_DATABASE || 'fedlearner',
    username: process.env.DB_USERNAME || 'fedlearner',
    password: process.env.DB_PASSWORD || 'fedlearner',
    host: process.env.DB_HOST || '127.0.0.1',
    port: Number(process.env.DB_PORT) || 3306,
    dialect: 'mysql',
  },
};
