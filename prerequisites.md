# Software Prerequisites & Setup Guide

Before you can run the **AI-Powered Learning Platform**, you need to ensure that your system has the required software installed. This document provides a clear list of all prerequisites, why they are needed, and where to download them.

---

## 1. Node.js & npm
**What it is:** A JavaScript runtime environment.
**Why you need it:** Required to install dependencies and run the React frontend development server (`npm start`).
**Download Link:** [Download Node.js](https://nodejs.org/)
**Installation Note:** Download the **LTS (Long Term Support)** version. The installation includes `npm` (Node Package Manager) automatically. Make sure to check the box that says "Add to PATH" during installation if prompted.

## 2. Python 3
**What it is:** A programming language.
**Why you need it:** Required to run the Flask backend, manage the SQLite database, and execute the AI generation scripts.
**Download Link:** [Download Python](https://www.python.org/downloads/)
**Installation Note:** Download Python 3.10 or newer. **CRITICAL:** During the Windows installation process, you *must* check the box at the bottom that says **"Add Python to PATH"** before clicking Install.

## 3. Git
**What it is:** A version control system.
**Why you need it:** Required for cloning the repository and managing your codebase history.
**Download Link:** [Download Git](https://git-scm.com/downloads)

## 4. Code Editor (Recommended)
**What it is:** An Integrated Development Environment (IDE) to write and edit your code.
**Why you need it:** To comfortably edit the project files, view the terminal, and manage your environment variables.
**Recommendation:** **Visual Studio Code (VS Code)**
**Download Link:** [Download VS Code](https://code.visualstudio.com/)

---

## Required Accounts & API Keys

To utilize the core Generative AI features of this application, you must obtain a free API key from Google.

### Google Gemini API Key
**What it is:** An authentication key that allows the backend to communicate with Google's large language models.
**Why you need it:** It powers the text generation, structuring the subtopics, and creating the core explanations for the learning platform.
**How to get it:**
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click on **"Get API key"** in the left sidebar.
4. Click **"Create API key in new project"**.
5. Copy the generated key.
**Where to put it:** Paste this key into your `backend/.env` file next to `GEMINI_API_KEY=`.

---

## Verification

Once you have installed the software, you can verify they are correctly installed by opening a terminal (Command Prompt or PowerShell) and typing:

```bash
node -v
npm -v
python --version
git --version
```
If each command returns a version number without errors, your machine is fully prepared to run the project!
