# 🌿 CampusFuel

> AI-powered nutrition & wellness tracker built for college students.

---

## 🚀 Running Locally (Quick Start)

You need **two terminals** — one for the backend, one for the frontend.

### Prerequisites

- Python 3.10+ (`python3 --version`)
- Node.js 18+ (`node --version`)
- A `.env` file in the project root (see Step 1)

---

### Step 1 — Clone the repo

```bash
git clone https://github.com/Arths17/CampusFuel.git
cd CampusFuel
```

> ✅ A `.env` file with all API keys is already included in the repo — no extra setup needed!

---

### Step 2 — Start the Backend (Terminal 1)

```bash
# Create virtualenv (first time only)
python3 -m venv .venv

# Activate it
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# Install dependencies (first time only)
pip install -r requirements.txt

# Start the backend
uvicorn main:app --reload --port 8000
```

✅ Backend running at: **http://localhost:8000**  
📖 API docs at: **http://localhost:8000/api/docs**

---

### Step 3 — Start the Frontend (Terminal 2)

```bash
# Install dependencies (first time only)
npm install

# Start Next.js dev server
npm run dev
```

✅ Frontend running at: **http://localhost:3000**

---

### Step 4 — Open the app

Go to **http://localhost:3000** in your browser.

1. Click **Sign Up** → create an account  
2. Complete the **survey** (19 questions about diet, goals, lifestyle)  
3. You'll land on the **Dashboard** — fully personalized!

---

## 📱 Pages

| Page | URL | Description |
|------|-----|-------------|
| Home | `/` | Landing page |
| Sign Up | `/signup` | Create account |
| Login | `/login` | Sign in |
| Survey | `/survey` | One-time profile setup (19 steps) |
| Dashboard | `/dashboard` | Nutrition overview + water tracker |
| Meals | `/meals` | Log & browse meals |
| Nutrition | `/nutrition` | Search food database (5,797 items) |
| Progress | `/progress` | Workout tracker + weekly chart |
| AI Chat | `/ai` | Gemini-powered nutrition assistant |
| Profile | `/Profile Page` | Account settings & change password |

---

## 🏗 Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 16, React 19 |
| Backend | FastAPI (Python) |
| Database | Supabase (PostgreSQL) |
| AI | Google Gemini 1.5 Flash |
| Auth | JWT (PyJWT + bcrypt) |
| Food DB | USDA FoodData Central (5,797 items) |

---

## 🛠 Troubleshooting

**"Cannot connect to backend" / all API calls fail**  
→ Make sure `uvicorn` is running in Terminal 1 on port 8000.  
→ Check: `curl http://localhost:8000/api/health`

**"Internal server error" on signup/login**  
→ Check your `.env` file has all 4 keys. Restart the backend after editing `.env`.

**Meals/water/workouts not saving (still show empty)**  
→ These need 3 Supabase tables. Run this SQL in [Supabase dashboard](https://supabase.com/dashboard) → SQL Editor:
```sql
CREATE TABLE water_logs (
  id SERIAL PRIMARY KEY,
  user_id INTEGER,
  date TEXT,
  glasses INTEGER
);
CREATE TABLE meals (
  id TEXT PRIMARY KEY,
  user_id INTEGER,
  type TEXT,
  items JSONB,
  total JSONB,
  date TEXT,
  timestamp TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE workouts (
  id TEXT PRIMARY KEY,
  user_id INTEGER,
  type TEXT,
  duration INTEGER,
  notes TEXT,
  date TEXT,
  timestamp TIMESTAMPTZ DEFAULT now()
);
```

**Port already in use**
```bash
lsof -ti :8000 | xargs kill -9   # free up backend port
lsof -ti :3000 | xargs kill -9   # free up frontend port
```

**`ModuleNotFoundError` on backend start**
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

---

## ✨ Features

- 🥗 **Personalized nutrition goals** — calculated from survey data (BMR + TDEE)
- 💧 **Water tracker** — click glasses to log daily intake
- 🍽 **Meal logger** — search & log from 5,797 USDA foods
- 💪 **Workout tracker** — log exercises & view history
- 🤖 **AI chat** — Gemini-powered nutrition assistant
- 📊 **Weekly calorie chart** — track trends across the week
- ✨ **Personalized AI insights** — tips generated from your profile

---

## 👥 Team

Built at HackTAMS 2026 by the Elden Ring Committee 🗡️
