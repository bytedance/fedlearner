const path = require('path');
const Sequelize = require('sequelize');
const { readdirSync } = require('../utils');
const getConfig = require('../utils/get_confg');

const config = getConfig({
  DB_DATABASE: process.env.DB_DATABASE,
  DB_USERNAME: process.env.DB_USERNAME,
  DB_PASSWORD: process.env.DB_PASSWORD,
  DB_HOST: process.env.DB_HOST,
  DB_PORT: process.env.DB_PORT,
  DB_DIALECT: process.env.DB_DIALECT,
  DB_SOCKET_PATH: process.env.DB_SOCKET_PATH,
});
const {
  DB_DATABASE, DB_USERNAME, DB_PASSWORD, DB_HOST, DB_PORT,
  DB_DIALECT, DB_SOCKET_PATH,
} = config;
const options = DB_SOCKET_PATH
  ? {
    dialect: DB_DIALECT,
    dialectOptions: {
      socketPath: DB_SOCKET_PATH,
    },
  }
  : {
    host: DB_HOST,
    port: DB_PORT,
    dialect: DB_DIALECT,
  };
const sequelize = new Sequelize(DB_DATABASE, DB_USERNAME, DB_PASSWORD, options);
const basename = path.basename(__filename);
const models = {};

readdirSync(__dirname)
  .filter((file) => !file.startsWith('.') && file !== basename && path.extname(file) === '.js')
  .forEach((file) => {
    const model = sequelize.import(path.join(__dirname, file));
    models[model.name] = model;
  });

Object.keys(models).forEach((modelName) => {
  if (models[modelName].associate) {
    models[modelName].associate(models);
  }
});

models.sequelize = sequelize;
models.Sequelize = Sequelize;

module.exports = models;
