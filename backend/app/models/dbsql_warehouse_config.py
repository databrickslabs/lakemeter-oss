"""DBSQL Warehouse Config model for sync_ref_dbsql_warehouse_config table."""
from sqlalchemy import Column, String, Integer
from app.database import Base


class DBSQLWarehouseConfig(Base):
    __tablename__ = "sync_ref_dbsql_warehouse_config"
    __table_args__ = {"schema": "lakemeter"}

    cloud = Column(String, primary_key=True)
    warehouse_type = Column(String, primary_key=True)
    warehouse_size = Column(String, primary_key=True)
    driver_count = Column(Integer)
    worker_count = Column(Integer)
    instance_type = Column(String)
