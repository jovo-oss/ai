import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from app.main import app

print('App loaded successfully')
print('Starting server on http://127.0.0.1:8000')
uvicorn.run(app, host='127.0.0.1', port=8000, log_level='info')
