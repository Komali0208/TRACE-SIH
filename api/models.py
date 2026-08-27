import json
from typing import Any, List, Optional
from pydantic import field_validator
from sqlalchemy.types import TypeDecorator, TEXT
from sqlmodel import Column, Field, SQLModel


class JSONText(TypeDecorator):
    """Custom SQLAlchemy type to store JSON objects/lists as TEXT in the database and expose them as parsed Python objects."""

    impl = TEXT
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Optional[str]:
        if value is None:
            return "[]"
        if isinstance(value, str):
            return value
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, (list, dict)):
            return value
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return []


class Camera(SQLModel, table=True):
    __tablename__ = "cameras"

    id: str = Field(primary_key=True)
    name: str
    lat: float
    lon: float
    road_name: Optional[str] = Field(default=None)
    direction: Optional[str] = Field(default=None)
    clip_url: Optional[str] = Field(default=None)


class CameraLink(SQLModel, table=True):
    __tablename__ = "camera_links"

    from_camera: str = Field(foreign_key="cameras.id", primary_key=True)
    to_camera: str = Field(foreign_key="cameras.id", primary_key=True)
    road_distance_m: int


class Sighting(SQLModel, table=True):
    __tablename__ = "sightings"

    id: str = Field(primary_key=True)
    plate_text: Optional[str] = Field(default=None, index=True)
    plate_confidence: Optional[float] = Field(default=None)
    camera_id: str = Field(foreign_key="cameras.id", index=True)
    ts: str = Field(index=True)
    track_id: Optional[int] = Field(default=None)
    frame_count: Optional[int] = Field(default=1)
    raw_reads: List[Any] = Field(
        default_factory=list,
        sa_column=Column("raw_reads", JSONText, nullable=False, server_default="[]"),
    )
    consensus_method: Optional[str] = Field(default="single_frame")
    crop_url: Optional[str] = Field(default=None)
    video_offset_s: Optional[float] = Field(default=None)
    flags: List[str] = Field(
        default_factory=list,
        sa_column=Column("flags", JSONText, nullable=False, server_default="[]"),
    )
    region_guess: Optional[str] = Field(default=None)

    @field_validator("raw_reads", "flags", mode="before")
    @classmethod
    def parse_json_if_str(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return v
        return v


class ReviewCase(SQLModel, table=True):
    __tablename__ = "review_cases"

    id: str = Field(primary_key=True)
    sighting_id: str = Field(foreign_key="sightings.id")
    flag_type: str
    status: str = Field(default="open", index=True)
    corrected_plate: Optional[str] = Field(default=None)
    reviewed_at: Optional[str] = Field(default=None)


class Watchlist(SQLModel, table=True):
    __tablename__ = "watchlist"

    plate_text: str = Field(primary_key=True)
    status: str
    reason: Optional[str] = Field(default=None)
    added_at: str


class Alert(SQLModel, table=True):
    __tablename__ = "alerts"

    id: str = Field(primary_key=True)
    sighting_id: str = Field(foreign_key="sightings.id")
    plate_text: str
    watchlist_status: str
    ts: str
    acknowledged: bool = Field(default=False, index=True)


class VehicleRegistry(SQLModel, table=True):
    """Mock VAHAN-shaped vehicle registry. Always seeded as is_mock_data=True."""

    __tablename__ = "vehicle_registry"

    plate_text: str = Field(primary_key=True)
    owner_name: str
    registration_date: str
    registering_authority: str
    vehicle_class: str
    make_model: str
    fuel_type: str
    registration_status: str
    fitness_valid_until: str
    insurance_valid_until: str
    puc_valid_until: str
    is_mock_data: bool = Field(default=True)
