# Here are your Instruction


# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn mediapipe opencv-python pillow motor python-dotenv python-multipart

# Update the .env file

uvicorn server:app --host 0.0.0.0 --port 8001 --reload

cd frontend

# Install yarn (if not installed)
npm install -g yarn

# Install dependencies
yarn install

# Update the .env file
yarn start
