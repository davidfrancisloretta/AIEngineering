from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from db import engine
from models import Base
from schemas import MetricCreate, MetricUpdate, MetricResponse
from dependencies import get_db
import services.metrics as metric_service
from routers import auth, config, data

app = FastAPI(title="Rave Analytics API")

# Create all tables on startup
Base.metadata.create_all(bind=engine)

# Routers
app.include_router(auth.router)
app.include_router(config.router)
app.include_router(data.router)


# -------------------------------
# Root Health Check
# -------------------------------
@app.get("/")
def root():
    return {"message": "AI Docker App Running Successfully"}


# -------------------------------
# Create Metric
# -------------------------------
@app.post("/metrics", response_model=MetricResponse, status_code=201)
def create_metric(data: MetricCreate, db: Session = Depends(get_db)):
    return metric_service.create_metric(db, data)


# -------------------------------
# Get All Metrics
# -------------------------------
@app.get("/metrics", response_model=list[MetricResponse])
def get_metrics(db: Session = Depends(get_db)):
    return metric_service.get_all_metrics(db)


# -------------------------------
# Get Single Metric
# -------------------------------
@app.get("/metrics/{metric_id}", response_model=MetricResponse)
def get_metric(metric_id: int, db: Session = Depends(get_db)):
    metric = metric_service.get_metric(db, metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    return metric


# -------------------------------
# Update Metric
# -------------------------------
@app.put("/metrics/{metric_id}", response_model=MetricResponse)
def update_metric(metric_id: int, data: MetricUpdate, db: Session = Depends(get_db)):
    metric = metric_service.update_metric(db, metric_id, data)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    return metric


# -------------------------------
# Delete Metric
# -------------------------------
@app.delete("/metrics/{metric_id}", status_code=204)
def delete_metric(metric_id: int, db: Session = Depends(get_db)):
    deleted = metric_service.delete_metric(db, metric_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Metric not found")
