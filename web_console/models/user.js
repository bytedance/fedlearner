module.exports = (sequelize, DataTypes) => {
  const User = sequelize.define('User', {
    id: {
      type: DataTypes.INTEGER,
      allowNull: false,
      autoIncrement: true,
      primaryKey: true,
    },
    username: {
      type: DataTypes.STRING(200),
      allowNull: false,
      unique: true,
    },
    password: {
      type: DataTypes.STRING(16),
      allowNull: false,
    },
    name: {
      type: DataTypes.STRING(200),
      allowNull: true,
      default: null,
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
    },
    is_admin: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
      default: false,
    },
  }, {
    tableName: 'users',
    paranoid: true,
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: 'updated_at',
    deletedAt: 'deleted_at',
  });

  return User;
};
