'use strict';

const etcd3 = require('etcd3');

module.exports = {
  up: async (queryInterface, Sequelize) => {
    let transaction = await queryInterface.sequelize.transaction();
    try {
      await queryInterface.createTable(
        'datasource_meta',
        {
          id: {
            type: Sequelize.INTEGER,
            allowNull: false,
            autoIncrement: true,
            primaryKey: true,
            comment: 'row id',
          },
          kv_key: {
            type: Sequelize.STRING(255),
            allowNull: false,
            unique: true,
            comment: 'key for kv store',
          },
          kv_value: {
            type: Sequelize.TEXT('long'),
            allowNull: true,
            default: null,
            comment: 'value for kv store',
          },
        },
        {}
      );

      if (process.env.ETCD_ADDR) {
        const client = new etcd3.Etcd3({
          hosts: process.env.ETCD_ADDR,
          grpcOptions: {
            'grpc.max_send_message_length': 2**31-1,
            'grpc.max_receive_message_length': 2**31-1,
          }
        });
        
        const values = await client.getAll().prefix('/').all();
        let rows = [];
        for (let key in values) {
          rows.push({
            kv_key: key,
            kv_value: values[key],
          });
        }
        for (let i = 0; i < rows.length; i += 1024) {
          await queryInterface.bulkInsert('datasource_meta', rows.slice(i, i + 1024));
        }
      }

      await transaction.commit();
      return Promise.resolve();
    } catch (err) {
      if (transaction) {
        await transaction.rollback();
      }
      return Promise.reject(err);
    }
  },

  down: async (queryInterface, Sequelize) => {
    return queryInterface.dropTable('datasource_meta');
  }
};
