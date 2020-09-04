'use strict';

module.exports = {
  up: async (queryInterface, Sequelize) => {
    let transaction = await queryInterface.sequelize.transaction();
    try {
      await queryInterface.addColumn(
        'jobs',
        'k8s_meta_snapshot',
        {
          type: Sequelize.TEXT('long'),
          allowNull: true,
          default: null,
          comment: 'k8s metadata snapshot before job is stopped',
        },
        { transaction }
      );
      await queryInterface.addColumn(
        'jobs',
        'status',
        {
          type: Sequelize.STRING(16),
          allowNull: true,
          default: 'started',
          comment: 'status of the current job: started | stopped | error',
        }
      );
      await queryInterface.sequelize.query(
        'UPDATE jobs SET status="started"',
        { transaction },
      );
      await queryInterface.addColumn(
        'jobs',
        'federation_id',
        {
          type: Sequelize.INTEGER,
          allowNull: true,
          default: null,
          comment: 'federation id of job',
        },
        { transaction }
      );
      await queryInterface.sequelize.query(`
        UPDATE jobs
        INNER JOIN tickets ON jobs.client_ticket_name = tickets.name
        SET jobs.federation_id = tickets.federation_id`,
        { transaction }
      );
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
    let transaction = await queryInterface.sequelize.transaction();
    try {
      await queryInterface.removeColumn('jobs', 'k8s_meta_snapshot', { transaction }),
      await queryInterface.removeColumn('jobs', 'status', { transaction }),
      await queryInterface.removeColumn('jobs', 'federation_id', { transaction }),
      await transaction.commit();
      return Promise.resolve();
    } catch (err) {
      if (transaction) {
        await transaction.rollback();
      }
      return Promise.reject(err);
    }
  }
};
