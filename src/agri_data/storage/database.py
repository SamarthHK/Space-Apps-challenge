"""
Database connection, session management, and table initialization.
Supports PostgreSQL/PostGIS and SQLite with automatic seed initialization.
"""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from agri_data.config import settings
from .models import Base, DataSource, Variable, CropSpecies, RotationEffect

# Create engine
engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions with automatic commit/rollback."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def seed_metadata(session: Session) -> None:
    """Populates master data sources, variables, and crop catalog from YAML if empty."""
    # 1. Sources
    sources_data = settings.sources_cfg.get("sources", {})
    for src_key, s_info in sources_data.items():
        existing = session.query(DataSource).filter_by(source_id=s_info.get("id", src_key)).first()
        if not existing:
            src = DataSource(
                source_id=s_info.get("id", src_key),
                name=s_info.get("name", src_key),
                domain=s_info.get("domain", "environmental"),
                access_type=s_info.get("type", "api"),
                base_url=s_info.get("base_url"),
                auth_required=s_info.get("auth_required", False),
                spatial_resolution_m=s_info.get("spatial_resolution_m"),
                temporal_type=s_info.get("temporal_type")
            )
            session.add(src)

    # 2. Variables
    vars_data = settings.variables_cfg.get("variables", {})
    for v_key, v_info in vars_data.items():
        existing = session.query(Variable).filter_by(variable_id=v_key).first()
        if not existing:
            v_range = v_info.get("valid_range", [None, None])
            var = Variable(
                variable_id=v_key,
                category=v_info.get("category", "general"),
                description=v_info.get("description", v_key),
                canonical_unit=v_info.get("canonical_unit", ""),
                depth_dependent=v_info.get("depth_dependent", False),
                temporal_type=v_info.get("temporal_type", "observation"),
                min_valid=v_range[0] if v_range and len(v_range) > 0 else None,
                max_valid=v_range[1] if v_range and len(v_range) > 1 else None
            )
            session.add(var)

    # 3. Crops
    crops_data = settings.crop_catalog_cfg.get("crops", {})
    for c_key, c_info in crops_data.items():
        existing = session.query(CropSpecies).filter_by(crop_id=c_info.get("id", c_key)).first()
        if not existing:
            crop = CropSpecies(
                crop_id=c_info.get("id", c_key),
                common_name=c_info.get("common_name", c_key),
                botanical_name=c_info.get("botanical_name", c_key),
                family=c_info.get("family", "Unknown"),
                crop_type=c_info.get("crop_type", "crop"),
                nitrogen_fixation_kg_ha=c_info.get("nitrogen_fixation_kg_ha", 0.0),
                residue_kg_ha=c_info.get("residue_kg_ha", 0.0),
                residue_c_n_ratio=c_info.get("residue_c_n_ratio")
            )
            session.add(crop)

    # 4. Rotation pairs
    rotation_pairs = settings.crop_catalog_cfg.get("rotation_compatibility", {}).get("pairs", [])
    for pair in rotation_pairs:
        p_crop = pair.get("previous")
        n_crop = pair.get("next")
        existing = session.query(RotationEffect).filter_by(previous_crop_id=p_crop, next_crop_id=n_crop).first()
        if not existing:
            re = RotationEffect(
                previous_crop_id=p_crop,
                next_crop_id=n_crop,
                compatibility_score=pair.get("compatibility_score", 5.0),
                expected_yield_delta_pct=pair.get("expected_yield_delta_pct", 0.0),
                notes=pair.get("benefit_notes")
            )
            session.add(re)

    session.commit()


def init_db() -> None:
    """Creates all database tables and seeds master variables and sources."""
    Base.metadata.create_all(bind=engine)
    with get_db_session() as session:
        seed_metadata(session)
