const mongoose = require('mongoose');

const graphSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true, // Now every graph MUST belong to a user
  },
  topic: { type: String, required: true },
  nodes: { type: Array, default: [] },
  edges: { type: Array, default: [] },
  createdAt: { type: Date, default: Date.now }
});

module.exports = mongoose.model('Graph', graphSchema);