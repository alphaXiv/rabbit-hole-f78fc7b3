# 🕳️ Rabbit Hole: AI-Powered Concept Visualizer
Rabbit Hole is an AI-powered, full-stack concept visualizer that dynamically generates and infinitely expands interactive learning maps using Gemini AI and React Flow. Built on the MERN stack, it features secure JWT authentication, automated mathematical graph layouts, and MongoDB persistence to save and export customized research sessions.

---

## ✨ Features
**AI Concept Generation:** Type in any topic, and the Gemini 2.5 Flash model deconstructs it into a structured, node-based learning map.

**Infinite Expansion:** Click on any node to dynamically generate deeper sub-concepts, allowing you to endlessly explore the "rabbit hole" of a specific topic.

**Auto-Balancing Layout:** Integrates the dagre directed graph engine to instantly calculate perfect spatial layouts, preventing node overlap no matter how large the map gets.

**Secure User Authentication:** Features a custom-built JWT (JSON Web Token) login and registration system with bcrypt password hashing to protect user accounts.

**Persistent Cloud Storage:** Connects to MongoDB, allowing users to safely store, retrieve, and manage their interactive JSON graph sessions in a personal library.

**High-Res Image Export:** Utilizes html-to-image to let users download massive, fully expanded learning maps as crisp, styled PNG files.

---

## 🛠️ Tech Stack
**Frontend (Client)**

React.js (Vite): Core framework for a fast, modern UI.

React Flow (@xyflow/react): Renders the interactive node-based canvas.

Dagre: Mathematical engine for automatic tree-layout calculations.

React Router: Handles navigation and protected dashboard routes.

HTML-to-Image: Captures the canvas and converts it to a downloadable PNG.

**Backend (API)**

Node.js & Express: Handles API routing and server logic.

Google Gemini AI API: Powers the dynamic JSON node generation.

MongoDB & Mongoose: NoSQL database and object modeling for user data and graph persistence.

JWT & Bcrypt: Manages secure, stateless user authentication.

---

## 🚀 Installation & Local Setup
Because this is a Full-Stack MERN application, you will need to run both the backend server and the frontend client simultaneously.

Prerequisites
Node.js installed on your machine.

A free MongoDB Atlas Cluster URI.

A free Google Gemini API Key.

1. Backend Setup (rabbit-hole-api)
```
Navigate to the backend directory and install the dependencies:
cd rabbit-hole-api
npm install

Create a .env file in the root of the rabbit-hole-api folder and add your specific keys:

PORT=5000
MONGODB_URI=your_mongodb_connection_string_here
GEMINI_API_KEY=your_gemini_api_key_here
JWT_SECRET=any_random_secure_string_for_tokens
Start the Express server:

npm start

The server will run on http://localhost:5000.
```

2. Frontend Setup (rabbit-hole-ui)
```
Open a new terminal tab, navigate to the frontend directory, and install dependencies:

cd rabbit-hole-ui
npm install

Start the Vite development server:

npm run dev
The React app will run on http://localhost:5173.
```

---

## 💡 How to Use
**Create an Account:** Open the frontend URL, click "Sign up", and register a new user. Log in to receive your authentication token.

**Start Exploring:** In the dashboard header, type a broad concept (e.g., "WebSockets" or "Machine Learning") and hit Explore.

**Dig Deeper:** Once the initial map renders, click on any individual node to ask the AI to generate three specific sub-concepts branching off of that exact point.

**Save Your Progress:** Click Save to DB to store the current state of your map. You can reload it anytime by opening the My Library sidebar.

**Export:** Click Download Map to export your entire visible graph as a high-quality PNG for your personal notes.

---

## 📄 License

This project is licensed under the MIT License. See the [MIT LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 👨‍💻 Author
Built by [Alankrit Agarwal](https://github.com/alankrit98)
