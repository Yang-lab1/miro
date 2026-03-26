from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.actors import CurrentActor, get_current_actor
from app.api.schemas.simulation import (
    SimulationCreateRequest,
    SimulationFilesRequest,
    SimulationPatchRequest,
    SimulationPrecheckRequest,
    SimulationPrecheckResponse,
    SimulationResponse,
)
from app.db.session import get_db
from app.modules.simulation import service as simulation_service

router = APIRouter(prefix="/simulations", tags=["simulations"])

DbSession = Annotated[Session, Depends(get_db)]
ActorDep = Annotated[CurrentActor, Depends(get_current_actor)]


@router.post("", response_model=SimulationResponse)
def create_simulation(
    payload: SimulationCreateRequest,
    db: DbSession,
    actor: ActorDep,
) -> SimulationResponse:
    return simulation_service.create_simulation(db, actor, payload)


@router.get("/{simulationId}", response_model=SimulationResponse)
def get_simulation(
    simulationId: str,
    db: DbSession,
    actor: ActorDep,
) -> SimulationResponse:
    return simulation_service.get_simulation(db, actor, simulationId)


@router.patch("/{simulationId}", response_model=SimulationResponse)
def update_simulation(
    simulationId: str,
    payload: SimulationPatchRequest,
    db: DbSession,
    actor: ActorDep,
) -> SimulationResponse:
    return simulation_service.update_simulation(db, actor, simulationId, payload)


@router.post("/{simulationId}/files", response_model=SimulationResponse)
def add_simulation_files(
    simulationId: str,
    payload: SimulationFilesRequest,
    db: DbSession,
    actor: ActorDep,
) -> SimulationResponse:
    return simulation_service.add_simulation_files(db, actor, simulationId, payload)


@router.post("/{simulationId}/strategy", response_model=SimulationResponse)
def generate_simulation_strategy(
    simulationId: str,
    db: DbSession,
    actor: ActorDep,
) -> SimulationResponse:
    return simulation_service.generate_simulation_strategy(db, actor, simulationId)


@router.post("/precheck", response_model=SimulationPrecheckResponse)
def simulation_precheck(
    payload: SimulationPrecheckRequest,
    db: DbSession,
    actor: ActorDep,
) -> SimulationPrecheckResponse:
    return simulation_service.run_precheck(db, actor, payload.countryKey)
