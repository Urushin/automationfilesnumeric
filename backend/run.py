import os
for key in list(os.environ.keys()):
    if os.environ[key] == "None":
        del os.environ[key]

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
