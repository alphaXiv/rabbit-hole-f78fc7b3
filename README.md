# Expanding Flow Maps — reduced-QM9 reproduction

[![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/alphaXiv/rabbit-hole-f78fc7b3/blob/main/notebooks/qm9_reproduction.py)

This public artifact tests the central molecule-generation claim from
[*Expanding Flow Maps* (arXiv:2607.21585)](https://arxiv.org/abs/2607.21585):
learned node insertion should remain effective at very small sampling-step
budgets relative to a matched fixed canvas.

**Assessment: partially reproduced.** At four steps, the paper reports fixed
→ expanding validity of 53.6%→91.7%, uniqueness of 63.1%→92.8%, and FCD of
3.008→1.780. We observe 51.8%→89.7% validity, but 97.9%→24.4% uniqueness and
2.44→11.31 FCD. At two steps, the paper's FCD improves 0.49→0.40; ours worsens
11.95→14.89. Disabling insertion improves our FCD further to 10.64, so only the
low-step validity direction is supported.

The bounded substitution keeps the named public QM9 task, RDKit metrics,
ChemNet FCD, active-node local times, learned insertion, noisy categorical
node/edge states, and a shared denoiser. It reduces the split from 100K to
20K/2K/2K, uses two seeds, trains a six-layer width-256 transformer for 30,000
steps, distills for 10,000 more, and evaluates 10,000 samples per condition.
No author implementation was public.

- [Illustrated report](reports/qm9-reproduction/report.md)
- [Self-contained tutorial notebook](notebooks/qm9_reproduction.py)
- [Machine-readable measurements](results/qm9_results.csv)
- Exact Molab URL: https://molab.marimo.io/github/alphaXiv/rabbit-hole-f78fc7b3/blob/main/notebooks/qm9_reproduction.py

Formal evidence used OpenResearch Kubernetes, four **NVIDIA RTX PRO 6000
Blackwell** GPUs per run, **16 GPUs peak**, and **1.178 hours actual elapsed wall
time** (2026-07-26 04:12:18–05:22:59 UTC).

## Experiment log

Every experiment inherited the exact command shown below from the frozen
baseline. Seed links point to the immutable code that produced the result.

| Branch / experiment | Purpose or change | Exact run command | Assessment / outcome | Compute |
|---|---|---|---|---|
| `main` | Public report, notebook, results, and reference implementation | Not run as an experiment (publication surface) | Presentation only | None |
| [EFlow seed 0](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/eflow-chemnet-recovery-seed-0), [seed 1](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/eflow-chemnet-recovery-seed-1) | Learned insertion; 4/10-step ChemNet evaluation | `bash scripts/run.sh` | Validity 89.7%/86.5%; uniqueness 24.4%/35.7%; FCD 11.31/9.06 | 4 GPUs/run; 8.8–9.0 min |
| [Fixed seed 0](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/fixed-canvas-chemnet-recovery-seed-0), [seed 1](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/fixed-canvas-chemnet-recovery-seed-1) | Matched fixed-canvas 4/10-step control | `bash scripts/run.sh` | Validity lower; uniqueness and FCD substantially better | 4 GPUs/run; 8.8–8.9 min |
| [Two-step EFM seed 0](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/distilled-two-step-efm-seed-0), [seed 1](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/distilled-two-step-efm-seed-1) | Consistency-distilled learned-insertion map | `bash scripts/run.sh` | 92.0% validity, 13.7% uniqueness, FCD 14.89 | 4 GPUs/run; 12.0–12.1 min |
| [Two-step fixed seed 0](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/distilled-two-step-fixed-map-seed-0), [seed 1](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/distilled-two-step-fixed-map-seed-1) | Compute-matched distilled fixed map | `bash scripts/run.sh` | 78.2% validity, 26.1% uniqueness, FCD 11.95 | 4 GPUs/run; 11.8–12.0 min |
| [No-insertion seed 0](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/distilled-two-step-insertion-disabled-ablation), [seed 1](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/distilled-two-step-insertion-disabled-ablation-s) | Distilled EFM with all positions exposed immediately | `bash scripts/run.sh` | 86.9% validity, 34.9% uniqueness, FCD 10.64; claimed mechanism direction absent | 4 GPUs/run; 11.9–12.0 min |

The prior Rabbit Hole application below is unrelated imported history. The
reproduction implementation lives in `src/`, `configs/`, `scripts/`, and
`.orx/`.

---

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
