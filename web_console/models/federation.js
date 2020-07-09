module.exports = (sequelize, DataTypes) => {
  const Federation = sequelize.define('Federation', {
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
    trademark: {
      type: DataTypes.STRING(200),
      allowNull: true,
      default: null,
      comment: 'display name of federation',
    },
    email: {
      type: DataTypes.STRING(255),
      allowNull: true,
      default: null,
    },
    tel: {
      type: DataTypes.STRING(15),
      allowNull: true,
      default: null,
      comment: 'business contact telephone',
    },
    avatar: {
      type: DataTypes.STRING(2048),
      allowNull: true,
      default: null,
      comment: 'URI of avatar',
    },
    k8s_settings: {
      type: DataTypes.TEXT('long'),
      allowNull: false,
      comment: 'settings for kubernetes cluster',
    },
  }, {
    tableName: 'federations',
    paranoid: true,
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: 'updated_at',
    deletedAt: 'deleted_at',
    getterMethods: {
      k8s_settings() {
        return JSON.parse(this.getDataValue('k8s_settings'));
      },
    },
    setterMethods: {
      k8s_settings(value) {
        this.setDataValue('k8s_settings', JSON.stringify(value));
      },
    },
  });

  return Federation;
};
