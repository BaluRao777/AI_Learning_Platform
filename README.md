# AI_Learning_Platform
AI learning platform that turns any topic into a personalised explanation and educational diagrams. A local Qwen2.5 model analyses the learner's level (school/college) and mode (learn/exam), Gemini writes the tailored explanation, and a locally run SANA 1.5 model draws the diagrams. Built with React and Flask.


An intelligent, full-stack educational web application designed to break down complex topics into easily digestible visual and textual content using Generative AI. 

## Features

- **Cinematic Experience**: Features a stunning video intro sequence that transitions directly into the application with a physics-based, bouncing text animation.
- **Neural Ribbon Cursor**: Custom high-performance Three.js WebGL cursor (TubesCursor) that creates a glowing fiber-optic trail responding to user mouse movements. It smartly fades out over interactive elements and pauses rendering entirely during video playback to optimize GPU/CPU usage.
- **Adaptive Learning Profiles**: Choose your academic level (`school` or `college`) and context mode (`learn` or `exam`) to receive AI-tailored explanations.
- **Generative Text & Diagrams**: Uses the Google Gemini AI for highly structured explanations and acts as a dynamic proxy for Pollinations.ai to fetch real-time educational diagrams.
- **Glassmorphism UI**: Beautiful dark-mode aesthetic with modern glass-pane UI components, interactive hover states, and smooth routing transitions.
- **Personalized History**: Secure user accounts (JWT authentication) with a dashboard to revisit past search queries and visualizations.

---

## Architecture Overview

The application follows a standard modern full-stack approach:

### Frontend
- **Framework**: React 19 / React Router v7
- **Animations**: Framer Motion
- **3D Graphics**: Three.js (EffectComposer, UnrealBloomPass)
- **Styling**: Vanilla CSS / Bootstrap grid overlay
- **Icons**: Lucide React

### Backend
- **Framework**: Python 3 / Flask
- **Database**: SQLite3 (Local file-based database)
- **Authentication**: JWT (JSON Web Tokens)
- **APIs**: Google Gemini SDK (`google-genai`), Requests (for image proxy)

---

## Local Development Setup

To run this application locally, you will need to run both the backend server and the frontend development server simultaneously.

### 1. Backend Setup (Flask)

1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your `.env` file inside the `backend` folder:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   JWT_SECRET=your_super_secret_jwt_key
   JWT_EXPIRES_HOURS=24
   FLASK_ENV=development
   HOST=0.0.0.0
   PORT=5000
   CORS_ORIGINS=http://localhost:3000
   ```
5. Initialize the Database and start the server:
   ```bash
   python init_db.py
   python app.py
   ```
   *The backend will now be running on `http://127.0.0.1:5000`.*

### 2. Frontend Setup (React)

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install the Node modules:
   ```bash
   npm install
   ```
3. *(Optional)* Configure your `.env.local` if necessary. By default, the API is configured to strictly hit `http://127.0.0.1:5000` to prevent modern browser IPv6 connection refusals.
4. Start the React development server:
   ```bash
   npm start
   ```
   *The application will open in your browser at `http://localhost:3000`.*

---

## Local AI upgrade (optional features)

The app can additionally analyse each request with a local Qwen model and generate images
with a local or LAN-served SANA 1.5 model fine-tuned on educational diagrams. Both features
are off by default and controlled by `backend/.env` flags (`ANALYZER_ENABLED`, `IMAGE_BACKEND`).
See `docs/ARCHITECTURE.md`, `docs/SETUP_LAPTOP_WINDOWS.md`, `docs/SETUP_WORKSTATION_UBUNTU.md`
and `docs/UPGRADE_REPORT.md`.

---

## Troubleshooting

- **Failed to fetch history (Network Error):** 
  Ensure your backend is running. The frontend is specifically hardcoded to communicate with `127.0.0.1:5000`. If you change your backend `HOST`, you must update `REACT_APP_API_BASE_URL` in the frontend.
- **Video Stuttering:**
  The landing page video is hardware-accelerated. If stuttering occurs, ensure your browser has hardware acceleration enabled. The 3D cursor automatically pauses while the video is playing to conserve resources.
- **Duplicate Images:**
  The AI image generation pipeline relies on pseudo-random seeds. If an image fails to generate, it will fall back to a safe SVG placeholder.
