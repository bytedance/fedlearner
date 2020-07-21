module.exports = (sequelize, DataTypes) => {
  const RawData = sequelize.define('RawData', {
    id: {
      type: DataTypes.INTEGER,
      allowNull: false,
      autoIncrement: true,
      primaryKey: true,
      comment: 'id',
    },
    name: {
      type: DataTypes.STRING(200),
      allowNull: false,
      unique: true,
      comment: 'unique, used for application scheduler',
    },
    user_id: {
      type: DataTypes.INTEGER,
      allowNull: false,
      comment: 'users.id',
    },
    federation_id: {
      type: DataTypes.INTEGER,
      allowNull: false,
      comment: 'federations.id',
    },
    input: {
      type: DataTypes.STRING(2048),
      allowNull: false,
      comment: 'root URI of data portal input',
    },
    output: {
      type: DataTypes.STRING(2048),
      allowNull: true,
      comment: 'root URI of data portal output',
    },
    output_partition_num: {
      type: DataTypes.INTEGER,
      allowNull: false,
      comment: 'output partition num',
    },
    data_portal_type: {
      type: DataTypes.STRING(20),
      allowNull: false,
      comment: 'Streaming | PSI',
    },
    context: {
      type: DataTypes.TEXT('long'),
      allowNull: true,
      default: null,
      comment: 'k8s YAML and job information',
    },
    remark: {
      type: DataTypes.TEXT,
      allowNull: true,
      default: null,
      comment: 'remark',
    },
    submitted: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
      default: false,
      comment: 'whether job is submitted',
    },
  }, {
    tableName: 'raw_datas',
    paranoid: true,
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: 'updated_at',
    deletedAt: 'deleted_at',
    getterMethods: {
      context() {
        const val = this.getDataValue('context');
        if (val) return JSON.parse(val);
        return null;
      },
    },
    setterMethods: {
      context(value) {
        this.setDataValue('context', value ? JSON.stringify(value) : null);
      },
    },
  });

  RawData.associate = (models) => {
    RawData.belongsTo(models.Federation, { as: 'federation', foreignKey: 'federation_id' });
    RawData.belongsTo(models.User, { as: 'user', foreignKey: 'user_id' });
  };

  return RawData;
};
