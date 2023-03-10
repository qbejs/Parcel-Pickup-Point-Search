import json
import logging as logger
from fastapi import APIRouter, Depends, HTTPException

from src.db import User
from src.middleware.role_middleware import RoleCheck
from src.models.requests.patch_point_request import PatchPointRequest
from src.models.requests.post_add_point_request import PostAddPointRequest
from src.models.point import PointModel
from src.models.users import current_active_user
from src.services.elastic import ESManager
from src.services.importers.xml_importer import XmlImporter

from src.services.point import PointService


router = APIRouter(
    prefix="/api",
)


@router.post("/point", response_model=PointModel)
async def add_point(
    point: PostAddPointRequest,
    service: PointService = Depends(PointService),
    user: User = Depends(current_active_user),
    role: bool = Depends(RoleCheck(role="ROLE_ADMIN")),
):
    try:
        resp = await service.add_point(point=point)

        return resp
    except Exception as _e:
        logger.error(
            "Cannot add point. Payload: %s | Error details: %s", point.json(), _e
        )
        raise HTTPException(500, "Cannot add new point. Contact with support.")


@router.patch("/point/{point}", response_model=PointModel)
async def patch_point(
    point: str,
    point_data: PatchPointRequest,
    service: ESManager = Depends(ESManager),
    user: User = Depends(current_active_user),
    role: bool = Depends(RoleCheck(role="ROLE_ADMIN")),
):
    try:
        data = PointModel.parse_raw(point_data.json())
        resp = await service.update(payload=data, resource_id=point)

        return resp
    except Exception as _e:
        logger.error("Cannot update point. Details: %s", _e)
        raise HTTPException(500, "Cannot update point.")


@router.delete("/point/{point}", response_model=PointModel)
async def delete_point(
    point: str,
    service: ESManager = Depends(ESManager),
    encoder: json.JSONEncoder = Depends(json.JSONEncoder),
    user: User = Depends(current_active_user),
    role: bool = Depends(RoleCheck(role="ROLE_ADMIN")),
):
    try:
        resp = await service.findOne(element_id=point)
        delete = await service.delete(
            payload=PointModel.parse_raw(
                encoder.encode(resp["hits"]["hits"][0]["_source"])
            )
        )

        return delete
    except Exception as _e:
        logger.error("Cannot delete point. Details: %s", _e)
        raise HTTPException(500, "Cannot delete point.")


@router.post("/point/import/{file_type}")
async def import_points(
    file: bytes,
    file_type: str,
    user: User = Depends(current_active_user),
    role: bool = Depends(RoleCheck(role="ROLE_ADMIN")),
):
    payload = file.decode()

    if file_type == "xml":
        service = XmlImporter()
        service.set_input(payload)
        await service.import_data()
        return {"status": "success"}

    raise HTTPException(400, "Unsupported file type")
