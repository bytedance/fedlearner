module.exports = (sequelize, DataTypes) => {
  const Job = sequelize.define('Job', {
    id: {
      type: DataTypes.INTEGER,
      allowNull: false,
      autoIncrement: true,
      primaryKey: true,
    },
    name: {
      type: DataTypes.STRING(200),
      allowNull: false,
      unique: true,
    },
    user_id: {
      type: DataTypes.INTEGER,
      allowNull: false,
      references: {
        model: 'users',
        key: 'id',
      },
    },
    job_type: {
      type: DataTypes.STRING(16),
      allowNull: false,
      comment: 'data_join | data_join_psi | training',
    },
    client_ticket_name: {
      type: DataTypes.STRING(200),
      allowNull: false,
    },
    server_ticket_name: {
      type: DataTypes.STRING(200),
      allowNull: false,
    },
    server_params: {
      type: DataTypes.TEXT('long'),
      allowNull: true,
      default: null,
    },
    client_params: {
      type: DataTypes.TEXT('long'),
      allowNull: true,
      default: null,
    },
  }, {
    tableName: 'jobs',
    paranoid: true,
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: 'updated_at',
    deletedAt: 'deleted_at',
    getterMethods: {
      server_params() {
        if (this.server_params) {
          return JSON.parse(this.server_params);
        }

        return null;
      },
      client_params() {
        if (this.client_params) {
          return JSON.parse(this.client_params);
        }

        return null;
      },
    },
    setterMethods: {
      server_params(value) {
        this.setDataValue('server_params', value ? JSON.stringify(value) : null);
      },
      client_params(value) {
        this.setDataValue('client_params', value ? JSON.stringify(value) : null);
      },
    },
  });

  Job.associate = (models) => {
    Job.belongsTo(models.User, { as: 'user', foreignKey: 'user_id' });
  };

  return Job;
};
