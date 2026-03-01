# 🌿 CampusFuel

> AI-powered nutrition & wellness tracker built for college students.

**Runs 100% locally — no cloud accounts, no API keys, no internet required.**

---

## 🚀 Running Locally — Complete Setup Guide

You need **three terminals**: one for the backend, one for the frontend, and one for the AI model.

---

### Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.9+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Ollama | latest | [ollama.com/download](https://ollama.com/download) |
| Git | any | `git --version` |

---

### Step 1 — Clone the repo

```bash
git clone https://github.com/Arths17/CampusFuel.git
cd CampusFuel
```

> ✅ A `.env` file is already included — no extra configuration needed.

---

### Step 2 — Install the AI model (one-time)

CampusFuel uses **Ollama** to run the AI chat locally. Install it, then pull the model:

```bash
# Pull the llama3.2 model (downloads ~2 GB, one-time only)
ollama pull llama3.2
```

Start the Ollama server (keep this running):

```bash
ollama serve
```

> ✅ Ollama runs at: **http://localhost:11434**  
> You can verify it's working: `curl http://localhost:11434/api/tags`

---

### Step 3 — Start the Backend (Terminal 2)

```bash
# Install Python dependencies (first time only)
pip install -r requirements.txt

# Start the FastAPI backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> ✅ Backend running at: **http://localhost:8000**  
> 📖 API docs at: **http://localhost:8000/api/docs**  
> 🩺 Health check: `curl http://localhost:8000/api/health`

**First time only — if you use a virtual environment:**
```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows
pip install -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

### Step 4 — Start the Frontend (Terminal 3)

```bash
# Install Node dependencies (first time only)
npm install

# Start Next.js dev server
npm run dev
```

> ✅ Frontend running at: **http://localhost:3000**

---

### Step 5 — Open the app

Go to **http://localhost:3000** in your browser.

#### Quick login with the demo account
| Field | Value |
|-------|-------|
| Username | `test123` |
| Password | `test123` |

This account works out of the box — no signup needed.

#### Create your own account
1. Click **Sign Up** → enter a username & password  
2. Complete the **onboarding survey** (height, weight, diet goals, activity level)  
3. You'll land on the **Dashboard** — fully personalized to your profile!

---

## 📱 Pages

| Page | URL | Description |
|------|-----|-------------|
| Home | `/` | Landing page |
| Sign Up | `/signup` | Create a new account |
| Login | `/login` | Sign in |
| Survey | `/survey` | One-time onboarding (diet, goals, lifestyle) |
| Dashboard | `/dashboard` | Calorie overview + water tracker |
| Meals | `/meals` | Log & browse meals |
| Nutrition | `/nutrition` | Search food database (5,797 USDA items) |
| Progress | `/progress` | Workout tracker + weekly chart |
| AI Chat | `/ai` | Ollama-powered nutrition assistant |
| Profile | `/profile` | Account settings & change password |

---

## 🏗 Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 16, React 19 |
| Backend | FastAPI (Python 3.9+) |
| Storage | Local JSON files (`users.json`, `user_profiles/`) |
| AI | Ollama + llama3.2 (runs locally) |
| Auth | JWT (PyJWT + bcrypt) |
| Food DB | USDA FoodData Central (5,797 items, bundled) |

> **No internet or cloud accounts required.** All data is stored locally in JSON files.

---

## 📁 Local Data Storage

All user data is stored locally in the project folder — no database setup needed:

| File / Folder | What it stores |
|---------------|----------------|
| `users.json` | Usernames & hashed passwords |
| `user_profiles/<username>.json` | Profile, survey answers, nutrition goals |
| `user_profiles/<username>_water.json` | Daily water intake logs |
| `user_profiles/<username>_meals.json` | Meal logs |

---

## 🛠 Troubleshooting

**Backend won't start — `ModuleNotFoundError`**
```bash
pip install -r requirements.txt
```

**Port already in use**
```bash
lsof -ti :8000 | xargs kill -9   # free backend port
lsof -ti :3000 | xargs kill -9   # free frontend port
```

**AI chat not responding**
```bash
# Make sure Ollama is running
ollama serve

# Verify the model is downloaded
ollama list   # should show llama3.2
```

**"Cannot connect to backend" / all API calls fail**  
→ Make sure the backend is running in its terminal on port 8000.  
→ Test: `curl http://localhost:8000/api/health` — should return `{"status":"ok",...}`

**Login says "User not found" for a new account**  
→ The account may not have saved. Check that `users.json` exists in the project root and is writable.

**Meals/water/workouts showing empty after refresh**  
→ Check that the `user_profiles/` folder exists and is writable:
```bash
ls user_profiles/
```

---

## ✨ Features

- 🥗 **Personalized nutrition goals** — BMR + TDEE calculated from your survey answers
- 💧 **Water tracker** — click to log daily glasses
- 🍽 **Meal logger** — search & log from 5,797 USDA foods
- 💪 **Workout tracker** — log exercises & view weekly history
- 🤖 **AI chat** — local Ollama nutrition assistant (no API key needed)
- 📊 **Weekly calorie chart** — visualize your intake over 7 days
- 👤 **Profile management** — update goals and change password

---

## 👥 Team

Built at HackTAMS 2026 by the Elden Ring Committee 🗡️
