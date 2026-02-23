from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models import DataIteration
from ..schemas import DataIterationCreate, DataIterationResponse
from ..core.data_iteration_engine import DataIterationEngine
from ..security import get_current_active_user

router = APIRouter(prefix="/data-iteration", tags=["data-iteration"])

@router.post("/", response_model=DataIterationResponse, status_code=status.HTTP_201_CREATED)
async def create_data_iteration(
    iteration: DataIterationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a new data iteration task"""
    try:
        engine = DataIterationEngine(db)
        result = await engine.create_iteration(iteration)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create data iteration: {str(e)}")

@router.get("/", response_model=List[DataIterationResponse])
async def get_data_iterations(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get list of data iterations with optional filtering"""
    try:
        engine = DataIterationEngine(db)
        iterations = await engine.get_iterations(skip=skip, limit=limit, status=status_filter)
        return iterations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data iterations: {str(e)}")

@router.get("/{iteration_id}", response_model=DataIterationResponse)
async def get_data_iteration(
    iteration_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get specific data iteration by ID"""
    try:
        engine = DataIterationEngine(db)
        iteration = await engine.get_iteration_by_id(iteration_id)
        if not iteration:
            raise HTTPException(status_code=404, detail="Data iteration not found")
        return iteration
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data iteration: {str(e)}")

@router.post("/{iteration_id}/start")
async def start_data_iteration(
    iteration_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Start a data iteration process"""
    try:
        engine = DataIterationEngine(db)
        result = await engine.start_iteration(iteration_id)
        return {"message": "Data iteration started successfully", "iteration_id": iteration_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start data iteration: {str(e)}")

@router.post("/{iteration_id}/pause")
async def pause_data_iteration(
    iteration_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Pause a running data iteration"""
    try:
        engine = DataIterationEngine(db)
        result = await engine.pause_iteration(iteration_id)
        return {"message": "Data iteration paused successfully", "iteration_id": iteration_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pause data iteration: {str(e)}")

@router.delete("/{iteration_id}")
async def delete_data_iteration(
    iteration_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Delete a data iteration"""
    try:
        engine = DataIterationEngine(db)
        result = await engine.delete_iteration(iteration_id)
        return {"message": "Data iteration deleted successfully", "iteration_id": iteration_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete data iteration: {str(e)}")