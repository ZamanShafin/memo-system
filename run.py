import uvicorn
import sys
import os

if __name__ == "__main__":
    print("Starting Inter-Office Memo Management System...")
    print("Accessible locally at: http://127.0.0.1:8000")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
