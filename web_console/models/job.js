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
    job_type: {
      type: DataTypes.STRING(16),
      allowNull: false,
      comment: 'data_join | psi_data_join | tree_model | nn_model',
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
    user_id: {
      type: DataTypes.INTEGER,
      allowNull: true,
      default: null,
    },
    k8s_name: {
      type: DataTypes.STRING(200),
      allowNull: false,
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
        const val = this.getDataValue('server_params');
        if (val) return JSON.parse(val);
        return null;
      },
      client_params() {
        const val = this.getDataValue('client_params');
        if (val) return JSON.parse(val);
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

  return Job;
};
