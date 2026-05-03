"""Router para gestion de equipos guardados."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/saved-teams", tags=["saved_teams"])

TEAMS_DB: dict[str, dict[str, Any]] = {}


class TeamMemberData(BaseModel):
    pokemon: str
    sprite: str
    types: list[str]
    ability: str
    item: str | None = None
    moves: list[str] = Field(default_factory=list)
    evs: dict[str, int] = Field(default_factory=dict)
    nature: str | None = None


class SavedTeamData(BaseModel):
    name: str
    format: str
    members: list[TeamMemberData]


class SavedTeamResponse(BaseModel):
    id: str
    name: str
    format: str
    members: list[TeamMemberData]
    created_at: str
    updated_at: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/", response_model=SavedTeamResponse)
async def save_team(team_data: SavedTeamData) -> SavedTeamResponse:
    """Guarda un equipo nuevo."""
    team_id = str(uuid.uuid4())
    now = _now_iso()
    team_record: dict[str, Any] = {
        "id": team_id,
        "name": team_data.name,
        "format": team_data.format,
        "members": [m.model_dump() for m in team_data.members],
        "created_at": now,
        "updated_at": now,
    }
    TEAMS_DB[team_id] = team_record
    return SavedTeamResponse(**team_record)


@router.get("/", response_model=list[SavedTeamResponse])
async def list_teams() -> list[SavedTeamResponse]:
    """Lista todos los equipos guardados."""
    teams = [SavedTeamResponse(**team) for team in TEAMS_DB.values()]
    teams.sort(key=lambda t: t.updated_at, reverse=True)
    return teams


@router.get("/{team_id}", response_model=SavedTeamResponse)
async def get_team(team_id: str) -> SavedTeamResponse:
    """Obtiene un equipo especifico."""
    if team_id not in TEAMS_DB:
        raise HTTPException(404, f"Team '{team_id}' not found")
    return SavedTeamResponse(**TEAMS_DB[team_id])


@router.put("/{team_id}", response_model=SavedTeamResponse)
async def update_team(team_id: str, team_data: SavedTeamData) -> SavedTeamResponse:
    """Actualiza un equipo existente."""
    if team_id not in TEAMS_DB:
        raise HTTPException(404, f"Team '{team_id}' not found")

    TEAMS_DB[team_id].update(
        {
            "name": team_data.name,
            "format": team_data.format,
            "members": [m.model_dump() for m in team_data.members],
            "updated_at": _now_iso(),
        }
    )
    return SavedTeamResponse(**TEAMS_DB[team_id])


@router.delete("/{team_id}")
async def delete_team(team_id: str) -> dict[str, str]:
    """Elimina un equipo."""
    if team_id not in TEAMS_DB:
        raise HTTPException(404, f"Team '{team_id}' not found")
    del TEAMS_DB[team_id]
    return {"message": f"Team '{team_id}' deleted successfully"}


@router.post("/{team_id}/export")
async def export_team(team_id: str, format: str = "showdown") -> dict[str, str]:
    """Exporta equipo a formato Showdown."""
    if team_id not in TEAMS_DB:
        raise HTTPException(404, f"Team '{team_id}' not found")

    team = TEAMS_DB[team_id]
    if format != "showdown":
        raise HTTPException(400, f"Export format '{format}' not supported")

    output_lines: list[str] = []
    for member in team["members"]:
        item_value = member.get("item")
        item = item_value if item_value else "No Item"
        lines = [f"{member['pokemon'].title()} @ {item}"]
        lines.append(f"Ability: {member['ability'].title()}")

        evs = member.get("evs") or {}
        if evs:
            ev_parts = [f"{value} {key.replace('_', ' ').title()}" for key, value in evs.items() if value > 0]
            if ev_parts:
                lines.append(f"EVs: {' / '.join(ev_parts)}")

        nature = member.get("nature")
        if nature:
            lines.append(f"{nature.title()} Nature")

        for move in member.get("moves", []):
            lines.append(f"- {move.title()}")

        output_lines.append("\n".join(lines))

    return {"format": "showdown", "content": "\n\n".join(output_lines)}

