'use strict';

module.exports = {
  up: async (queryInterface, Sequelize) => {
    let transaction = await queryInterface.sequelize.transaction();
    try {
      let schema = await queryInterface.showAllSchemas();
      let tables = [];
      schema.forEach(x => {tables.push(x.Tables_in_fedlearner)});

      if (!tables.includes('federations')) {
        await queryInterface.createTable(
          'federations',
          {
            id: {
              type: Sequelize.INTEGER,
              allowNull: false,
              autoIncrement: true,
              primaryKey: true,
              comment: 'id',
            },
            name: {
              type: Sequelize.STRING(200),
              allowNull: false,
              unique: true,
              comment: 'identifier of federation',
            },
            trademark: {
              type: Sequelize.STRING(200),
              allowNull: true,
              default: null,
              comment: 'legal name of federation',
            },
            email: {
              type: Sequelize.STRING(255),
              allowNull: true,
              default: null,
              comment: 'email',
            },
            tel: {
              type: Sequelize.STRING(15),
              allowNull: true,
              default: null,
              comment: 'business contact telephone',
            },
            avatar: {
              type: Sequelize.STRING(2048),
              allowNull: true,
              default: null,
              comment: 'URI of avatar',
            },
            k8s_settings: {
              type: Sequelize.TEXT('long'),
              allowNull: false,
              comment: 'settings of kubernetes cluster',
            },
            created_at: {
              type: Sequelize.DATE,
              allowNull: false,
            },
            updated_at: {
              type: Sequelize.DATE,
              allowNull: false,
            },
            deleted_at: {
              type: Sequelize.DATE,
              allowNull: true,
            }
          },
          {}
        );
      }

      if (!tables.includes('jobs')) {
        await queryInterface.createTable(
          'jobs',
          {
            id: {
              type: Sequelize.INTEGER,
              allowNull: false,
              autoIncrement: true,
              primaryKey: true,
              comment: 'id',
            },
            name: {
              type: Sequelize.STRING(200),
              allowNull: false,
              unique: true,
              comment: 'identifier of job',
            },
            job_type: {
              type: Sequelize.STRING(16),
              allowNull: false,
              comment: 'data_join | psi_data_join | tree_model | nn_model',
            },
            client_ticket_name: {
              type: Sequelize.STRING(200),
              allowNull: false,
              comment: 'tickets.name',
            },
            server_ticket_name: {
              type: Sequelize.STRING(200),
              allowNull: false,
              comment: 'tickets.name',
            },
            server_params: {
              type: Sequelize.TEXT('long'),
              allowNull: true,
              default: null,
              comment: 'resource config of Kubernetes',
            },
            client_params: {
              type: Sequelize.TEXT('long'),
              allowNull: true,
              default: null,
              comment: 'resource config of Kubernetes',
            },
            user_id: {
              type: Sequelize.INTEGER,
              allowNull: true,
              default: null,
              comment: 'users.id',
            },
            created_at: {
              type: Sequelize.DATE,
              allowNull: false,
            },
            updated_at: {
              type: Sequelize.DATE,
              allowNull: false,
            },
            deleted_at: {
              type: Sequelize.DATE,
              allowNull: true,
            }
          },
          {}
        );
      }

      if (!tables.includes('raw_datas')) {
        await queryInterface.createTable(
          'raw_datas',
          {
            id: {
              type: Sequelize.INTEGER,
              allowNull: false,
              autoIncrement: true,
              primaryKey: true,
              comment: 'id',
            },
            name: {
              type: Sequelize.STRING(200),
              allowNull: false,
              unique: true,
              comment: 'unique, used for application scheduler',
            },
            user_id: {
              type: Sequelize.INTEGER,
              allowNull: false,
              comment: 'users.id',
            },
            federation_id: {
              type: Sequelize.INTEGER,
              allowNull: false,
              comment: 'federations.id',
            },
            input: {
              type: Sequelize.STRING(2048),
              allowNull: false,
              comment: 'root URI of data portal input',
            },
            output: {
              type: Sequelize.STRING(2048),
              allowNull: true,
              comment: 'root URI of data portal output',
            },
            output_partition_num: {
              type: Sequelize.INTEGER,
              allowNull: false,
              comment: 'output partition num',
            },
            data_portal_type: {
              type: Sequelize.STRING(20),
              allowNull: false,
              comment: 'Streaming | PSI',
            },
            context: {
              type: Sequelize.TEXT('long'),
              allowNull: true,
              default: null,
              comment: 'k8s YAML and job information',
            },
            remark: {
              type: Sequelize.TEXT,
              allowNull: true,
              default: null,
              comment: 'remark',
            },
            submitted: {
              type: Sequelize.BOOLEAN,
              allowNull: true,
              default: false,
              comment: 'whether job is submitted',
            },
            created_at: {
              type: Sequelize.DATE,
              allowNull: false,
            },
            updated_at: {
              type: Sequelize.DATE,
              allowNull: false,
            },
            deleted_at: {
              type: Sequelize.DATE,
              allowNull: true,
            }
          },
          {}
        );
      }

      if (!tables.includes('tickets')) {
        await queryInterface.createTable(
          'tickets',
          {
            id: {
              type: Sequelize.INTEGER,
              allowNull: false,
              autoIncrement: true,
              primaryKey: true,
              comment: 'id',
            },
            name: {
              type: Sequelize.STRING(200),
              allowNull: false,
              unique: true,
              comment: 'identifier of ticket',
            },
            federation_id: {
              type: Sequelize.INTEGER,
              allowNull: false,
              comment: 'federations.id',
            },
            user_id: {
              type: Sequelize.INTEGER,
              allowNull: false,
              comment: 'users.id',
            },
            job_type: {
              type: Sequelize.STRING(16),
              allowNull: false,
              comment: 'data_join | psi_data_join | tree_model | nn_model',
            },
            role: {
              type: Sequelize.STRING(16),
              allowNull: false,
              comment: 'Leader | Follower',
            },
            sdk_version: {
              type: Sequelize.STRING(64),
              allowNull: true,
              default: null,
              comment: 'docker image tag',
            },
            expire_time: {
              type: Sequelize.DATE,
              allowNull: true,
              comment: 'time to revoke ticket',
            },
            remark: {
              type: Sequelize.TEXT,
              allowNull: true,
              default: null,
              comment: 'remark',
            },
            public_params: {
              type: Sequelize.TEXT('long'),
              allowNull: true,
              default: null,
              comment: 'public params of Kubernetes',
            },
            private_params: {
              type: Sequelize.TEXT('long'),
              allowNull: true,
              default: null,
              comment: 'private params of Kubernetes',
            },
            created_at: {
              type: Sequelize.DATE,
              allowNull: false,
            },
            updated_at: {
              type: Sequelize.DATE,
              allowNull: false,
            },
            deleted_at: {
              type: Sequelize.DATE,
              allowNull: true,
            }
          },
          {}
        );
      }

      if (!tables.includes('users')) {
        await queryInterface.createTable(
          'users',
          {
            id: {
              type: Sequelize.INTEGER,
              allowNull: false,
              autoIncrement: true,
              primaryKey: true,
              comment: 'id',
            },
            username: {
              type: Sequelize.STRING(200),
              allowNull: false,
              unique: true,
              comment: 'identifier of user',
            },
            password: {
              type: Sequelize.STRING(16),
              allowNull: false,
              comment: 'password',
            },
            name: {
              type: Sequelize.STRING(200),
              allowNull: true,
              default: null,
              comment: 'name',
            },
            email: {
              type: Sequelize.STRING(255),
              allowNull: true,
              default: null,
              comment: 'email',
            },
            tel: {
              type: Sequelize.STRING(15),
              allowNull: true,
              default: null,
              comment: 'telephone',
            },
            avatar: {
              type: Sequelize.STRING(2048),
              allowNull: true,
              default: null,
              comment: 'avatar',
            },
            is_admin: {
              type: Sequelize.BOOLEAN,
              allowNull: true,
              default: false,
              comment: 'whether user is admin',
            },
            created_at: {
              type: Sequelize.DATE,
              allowNull: false,
            },
            updated_at: {
              type: Sequelize.DATE,
              allowNull: false,
            },
            deleted_at: {
              type: Sequelize.DATE,
              allowNull: true,
            }
          },
          {}
        );
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
    let transaction = await queryInterface.sequelize.transaction();
    try {
      await queryInterface.dropTable('federations');
      await queryInterface.dropTable('jobs');
      await queryInterface.dropTable('raw_datas');
      await queryInterface.dropTable('tickets');
      await queryInterface.dropTable('users');
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
