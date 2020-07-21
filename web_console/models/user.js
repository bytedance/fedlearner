module.exports = (sequelize, DataTypes) => {
  const User = sequelize.define('User', {
    id: {
      type: DataTypes.INTEGER,
      allowNull: false,
      autoIncrement: true,
      primaryKey: true,
      comment: 'id',
    },
    username: {
      type: DataTypes.STRING(200),
      allowNull: false,
      unique: true,
      comment: 'identifier of user',
    },
    password: {
      type: DataTypes.STRING(16),
      allowNull: false,
      comment: 'password',
    },
    name: {
      type: DataTypes.STRING(200),
      allowNull: true,
      default: null,
      comment: 'name',
    },
    email: {
      type: DataTypes.STRING(255),
      allowNull: true,
      default: null,
      comment: 'email',
    },
    tel: {
      type: DataTypes.STRING(15),
      allowNull: true,
      default: null,
      comment: 'telephone',
    },
    avatar: {
      type: DataTypes.STRING(2048),
      allowNull: true,
      default: null,
      comment: 'avatar',
    },
    is_admin: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
      default: false,
      comment: 'whether user is admin',
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
