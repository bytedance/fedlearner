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
      type: DataTypes.STRING(2083),
      allowNull: true,
      default: null,
      comment: 'URI of avatar',
    },
    domain: {
      type: DataTypes.STRING(253),
      allowNull: true,
      default: null,
      comment: 'the web console endpoint',
    },
    token: {
      type: DataTypes.STRING(16),
      allowNull: true,
      default: null,
      comment: 'client-side certificate',
    },
    cipher: {
      type: DataTypes.STRING(200),
      allowNull: true,
      default: null,
      comment: 'used for authorization. null stands for a passive pair, others stands for initiative pair',
    },
    k8s_settings: {
      type: DataTypes.TEXT('long'),
      allowNull: true,
      default: null,
      comment: 'settings for kubernetes cluster',
    },
  }, {
    tableName: 'federations',
    paranoid: true,
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: 'updated_at',
    deletedAt: 'deleted_at',
  });

  return Federation;
};
