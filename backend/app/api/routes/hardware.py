from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.actors import CurrentActor, get_current_actor
from app.api.schemas.hardware import (
    HardwareDeviceLogResponse,
    HardwareDeviceSummaryResponse,
    HardwareDeviceSyncRecordResponse,
    HardwareSyncRequest,
    HardwareSyncResponse,
)
from app.db.session import get_db
from app.modules.hardware import service as hardware_service

router = APIRouter(prefix="/hardware", tags=["hardware"])

DbSession = Annotated[Session, Depends(get_db)]
ActorDep = Annotated[CurrentActor, Depends(get_current_actor)]


@router.get("/devices", response_model=list[HardwareDeviceSummaryResponse])
def list_devices(
    db: DbSession,
    actor: ActorDep,
) -> list[HardwareDeviceSummaryResponse]:
    return hardware_service.list_devices(db, actor)


@router.post("/devices/{device_id}/connect", response_model=HardwareDeviceSummaryResponse)
def connect_device(
    device_id: str,
    db: DbSession,
    actor: ActorDep,
) -> HardwareDeviceSummaryResponse:
    return hardware_service.connect_device(db, actor, device_id)


@router.post("/devices/{device_id}/disconnect", response_model=HardwareDeviceSummaryResponse)
def disconnect_device(
    device_id: str,
    db: DbSession,
    actor: ActorDep,
) -> HardwareDeviceSummaryResponse:
    return hardware_service.disconnect_device(db, actor, device_id)


@router.post("/devices/{device_id}/sync", response_model=HardwareSyncResponse)
def sync_device(
    device_id: str,
    payload: HardwareSyncRequest,
    db: DbSession,
    actor: ActorDep,
) -> HardwareSyncResponse:
    return hardware_service.sync_device(db, actor, device_id, payload)


@router.get("/devices/{device_id}/logs", response_model=list[HardwareDeviceLogResponse])
def get_device_logs(
    device_id: str,
    db: DbSession,
    actor: ActorDep,
) -> list[HardwareDeviceLogResponse]:
    return hardware_service.get_device_logs(db, actor, device_id)


@router.get(
    "/devices/{device_id}/sync-records",
    response_model=list[HardwareDeviceSyncRecordResponse],
)
def get_device_sync_records(
    device_id: str,
    db: DbSession,
    actor: ActorDep,
) -> list[HardwareDeviceSyncRecordResponse]:
    return hardware_service.get_device_sync_records(db, actor, device_id)
