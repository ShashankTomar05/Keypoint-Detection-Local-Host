# Setup

python -m venv venv

# Activate virtual environment on Windows
venv\Scripts\activate

# Activate virtual environment on Mac/Linux
source venv/bin/activate

pip install -r backend/requirements.txt

# Update backend/.env

# Install frontend dependencies

corepack enable
corepack prepare yarn@1.22.22 --activate
cd frontend
yarn install
cd ..

# Run frontend and backend together

powershell -ExecutionPolicy Bypass -File .\start-app.ps1

# Render deployment

Build command:
pip install -r backend/requirements.txt && corepack enable && corepack prepare yarn@1.22.22 --activate && cd frontend && yarn install --frozen-lockfile && yarn build

Start command:
cd backend && python -m uvicorn server:app --host 0.0.0.0 --port $PORT
