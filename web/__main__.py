if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", "8765"))
    uvicorn.run("web.server:app", host="127.0.0.1", port=port, reload=False)
