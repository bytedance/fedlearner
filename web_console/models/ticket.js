module.exports = (sequelize, DataTypes) => {
  const Ticket = sequelize.define('Ticket', {
    id: {
      type: DataTypes.INTEGER,
      allowNull: false,
      autoIncrement: true,
      primaryKey: true,
    },
    name: {
      type: DataTypes.STRING(200),
      allowNull: false,
    },
    state: {
      type: DataTypes.STRING(16),
      allowNull: true,
      default: 'pending',
      comment: 'pending | fulfilled | rejected',
    },
    callback: {
      type: DataTypes.TEXT,
      allowNull: true,
      default: null,
      comment: 'reserved field, a JSON-RPC call used for webhook',
    },
    creator: {
      type: DataTypes.STRING(200),
      allowNull: false,
    },
    log: {
      type: DataTypes.TEXT('long'),
      allowNull: true,
      default: null,
    },
  }, {
    tableName: 'tickets',
    paranoid: true,
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: 'updated_at',
    deletedAt: 'deleted_at',
  });

  return Ticket;
};
