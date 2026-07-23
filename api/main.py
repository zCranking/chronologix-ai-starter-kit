from fastapi import FastAPI

app = FastAPI(title="Chronologix API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
