const path = require('path');
const Sequelize = require('sequelize');
const config = require('../db.config');
const { readdirSync } = require('../utils');

const env = process.env.NODE_ENV || 'development';
const { database, username, password, host, port, dialect } = config[env];
const sequelize = new Sequelize(database, username, password, {
  host, port, dialect,
});
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
