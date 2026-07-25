const express = require('express');
const cors = require('cors');
const { GoogleGenerativeAI } = require('@google/generative-ai');
require('dotenv').config();
const mongoose = require('mongoose');
const Graph = require('./models/Graph');

const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

const app = express();
const PORT = process.env.PORT || 5000;

const User = require('./models/User');
const auth = require('./middleware/auth');

// --- DATABASE CONNECTION ---
mongoose.connect(process.env.MONGODB_URI)
  .then(() => console.log('✅ Connected to MongoDB'))
  .catch((err) => console.error('❌ MongoDB connection error:', err));

// Initialize the AI
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

app.use(cors());
app.use(express.json({ limit: '10mb' }));

// The prompt ensuring strict JSON and coordinate generation
const SYSTEM_PROMPT = `
You are an expert concept deconstructor. 
When given a topic, break it down into 3-5 core sub-concepts.
You MUST output raw JSON only, with no markdown formatting.

The JSON must exactly match this schema:
{
  "nodes": [
    { 
      "id": "unique-string", 
      "position": { "x": 0, "y": 0 }, 
      "data": { "label": "Concept Name" } 
    }
  ],
  "edges": [
    { "id": "unique-edge-string", "source": "parent-node-id", "target": "child-node-id" }
  ]
}

Important formatting rules:
1. Make the 'id' for the root node simply "root".
2. Space the 'x' and 'y' coordinates out so the nodes don't overlap (e.g., x: 250, y: 0 for root, then spread sub-concepts across y: 150 and x: 50, 250, 450).
`;

app.post('/api/generate', async (req, res) => {
  const { topic } = req.body;

  if (!topic) {
    return res.status(400).json({ error: 'Topic is required' });
  }

  try {
    console.log(`Generating Rabbit Hole for: ${topic}`);

    // Call the Gemini model, forcing JSON output
    const model = genAI.getGenerativeModel({ 
        model: "gemini-2.5-flash",
        generationConfig: { responseMimeType: "application/json" }
    });

    const prompt = `${SYSTEM_PROMPT}\n\nGenerate the concept map for this topic: "${topic}"`;
    
    const result = await model.generateContent(prompt);
    const responseText = result.response.text().replace(/```json/g, '').replace(/```/g, '').trim();
    
    // Parse the AI's string response into an actual JSON object
    const graphData = JSON.parse(responseText);

    // Generate a random unique suffix for this specific batch
    const uniqueSuffix = Date.now().toString(36) + Math.random().toString(36).substring(2, 6);
    const idMap = {};

    // Remap Node IDs
    graphData.nodes = graphData.nodes.map((node, i) => {
      // Keep the original 'root' ID intact for the first generation
      if (node.id === 'root') {
        idMap[node.id] = 'root';
        return node;
      }
      // Give every other node a strictly unique ID
      const newId = `node-${uniqueSuffix}-${i}`;
      idMap[node.id] = newId;
      return { ...node, id: newId };
    });

    // Remap Edge Targets and Sources to match the new Node IDs
    graphData.edges = graphData.edges.map((edge, i) => {
      return {
        ...edge,
        id: `edge-${uniqueSuffix}-${i}`,
        // If the source/target is in our map, update it. 
        // If not (like the parentNodeId from the frontend), leave it alone.
        source: idMap[edge.source] || edge.source, 
        target: idMap[edge.target] || edge.target 
      };
    });

    // Send the newly mapped data to React
    res.json(graphData);

  } catch (error) {
    console.error('AI Generation Error:', error);
    res.status(500).json({ error: 'Failed to generate concept map' });
  }
});

// THE EXPAND ROUTE
app.post('/api/expand', async (req, res) => {
  const { parentNodeId, concept, parentPosition } = req.body;

  if (!concept) {
    return res.status(400).json({ error: 'Concept is required' });
  }

  try {
    console.log(`Expanding Rabbit Hole for: ${concept}`);

    const model = genAI.getGenerativeModel({ 
        model: "gemini-2.5-flash",
        generationConfig: { responseMimeType: "application/json" }
    });

    const EXPAND_PROMPT = `
    You are an expert concept deconstructor. Break down the concept: "${concept}" into 3 specific sub-concepts.
    You MUST output raw JSON only matching this schema:
    {
      "nodes": [ { "id": "unique-string", "position": { "x": 0, "y": 0 }, "data": { "label": "Sub-concept" } } ],
      "edges": [ { "id": "unique-edge", "source": "${parentNodeId}", "target": "child-node-id" } ]
    }
    
    CRITICAL INSTRUCTIONS:
    1. Every edge's "source" MUST be exactly "${parentNodeId}".
    2. Position the new nodes below the parent. The parent's Y position is ${parentPosition.y}. Make the new nodes' Y position at least ${parentPosition.y + 150}.
    3. Spread the X coordinates out widely (e.g., -200, 0, 200) relative to the parent's X position of ${parentPosition.x} so they do not overlap.
    4. Ensure all string values inside the JSON are properly escaped. Do not use unescaped quotation marks inside the labels.
    `;
    
    const result = await model.generateContent(EXPAND_PROMPT);
    let responseText = result.response.text();

    // 1. Strip out markdown code blocks if the AI accidentally included them
    responseText = responseText.replace(/```json/g, '').replace(/```/g, '').trim();

    // 2. Parse the cleaned string
    const graphData = JSON.parse(responseText);

    // Generate a random unique suffix for this specific batch
    const uniqueSuffix = Date.now().toString(36) + Math.random().toString(36).substring(2, 6);
    const idMap = {};

    // Remap Node IDs
    graphData.nodes = graphData.nodes.map((node, i) => {
      // Keep the original 'root' ID intact for the first generation
      if (node.id === 'root') {
        idMap[node.id] = 'root';
        return node;
      }
      // Give every other node a strictly unique ID
      const newId = `node-${uniqueSuffix}-${i}`;
      idMap[node.id] = newId;
      return { ...node, id: newId };
    });

    // Remap Edge Targets and Sources to match the new Node IDs
    graphData.edges = graphData.edges.map((edge, i) => {
      return {
        ...edge,
        id: `edge-${uniqueSuffix}-${i}`,
        // If the source/target is in our map, update it. 
        // If not (like the parentNodeId from the frontend), leave it alone.
        source: idMap[edge.source] || edge.source, 
        target: idMap[edge.target] || edge.target 
      };
    });

    // Send the newly mapped data to React
    res.json(graphData);

  } catch (error) {
    console.error('AI Expansion Error:', error);
    res.status(500).json({ error: 'Failed to expand concept' });
  }
});

// Save a Graph
app.post('/api/graphs', auth, async (req, res) => {
  const { topic, nodes, edges } = req.body;

  if (!topic || !nodes || !edges) {
    return res.status(400).json({ error: 'Missing required graph data' });
  }

  try {
    const newGraph = new Graph({ 
      userId: req.user.id, // <-- We get this securely from the JWT token, not the frontend!
      topic, 
      nodes, 
      edges 
    });
    
    const savedGraph = await newGraph.save();
    res.status(201).json(savedGraph);
  } catch (error) {
    console.error('Save Error:', error);
    res.status(500).json({ error: 'Failed to save graph' });
  }
});

// Get All Saved Graphs
app.get('/api/graphs', auth, async (req, res) => {
  try {
    // Filter the database so it ONLY returns graphs matching the logged-in user
    const graphs = await Graph.find({ userId: req.user.id })
                              .select('topic createdAt')
                              .sort({ createdAt: -1 });
    res.json(graphs);
  } catch (error) {
    console.error('Fetch Error:', error);
    res.status(500).json({ error: 'Failed to fetch graphs' });
  }
});

// Get a Specific Graph by ID
app.get('/api/graphs/:id', auth, async (req, res) => {
  try {
    const graph = await Graph.findById(req.params.id);
    if (!graph) return res.status(404).json({ error: 'Graph not found' });
    
    // Make sure the person requesting this graph actually owns it
    if (graph.userId.toString() !== req.user.id) {
      return res.status(401).json({ error: 'Not authorized to view this graph' });
    }

    res.json(graph);
  } catch (error) {
    console.error('Fetch Error:', error);
    res.status(500).json({ error: 'Failed to fetch the specific graph' });
  }
});

// --- AUTHENTICATION ROUTES ---

// 1. REGISTER A NEW USER
app.post('/api/auth/register', async (req, res) => {
  const { username, password } = req.body;

  try {
    // Check if user already exists
    const existingUser = await User.findOne({ username });
    if (existingUser) return res.status(400).json({ error: 'Username already taken' });

    // Hash the password (salt it 10 times)
    const salt = await bcrypt.genSalt(10);
    const hashedPassword = await bcrypt.hash(password, salt);

    // Save the new user
    const newUser = new User({ username, password: hashedPassword });
    await newUser.save();

    res.status(201).json({ message: 'User created successfully!' });
  } catch (error) {
    console.error('Registration Error:', error);
    res.status(500).json({ error: 'Server error during registration' });
  }
});

// 2. LOGIN AN EXISTING USER
app.post('/api/auth/login', async (req, res) => {
  const { username, password } = req.body;

  try {
    // Find the user
    const user = await User.findOne({ username });
    if (!user) return res.status(400).json({ error: 'Invalid credentials' });

    // Check if password matches the hashed password in DB
    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) return res.status(400).json({ error: 'Invalid credentials' });

    // Generate the JWT Token (The VIP Pass)
    const token = jwt.sign(
      { id: user._id, username: user.username }, 
      process.env.JWT_SECRET, 
      { expiresIn: '24h' } // Token expires in 1 day
    );

    res.json({ token, username: user.username });
  } catch (error) {
    console.error('Login Error:', error);
    res.status(500).json({ error: 'Server error during login' });
  }
});

app.listen(PORT, () => {
  console.log(`Rabbit Hole API running on http://localhost:${PORT}`);
});
