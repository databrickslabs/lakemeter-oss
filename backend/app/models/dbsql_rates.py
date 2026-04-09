"""DBSQL Rates model for sync_product_dbsql_rates table."""
from sqlalchemy import Column, String, Float, Integer
from app.database import Base


class DBSQLRates(Base):
    __tablename__ = "sync_product_dbsql_rates"
    __table_args__ = {"schema": "lakemeter"}

    cloud = Column(String, primary_key=True)
    warehouse_type = Column(String, primary_key=True)
    warehouse_size = Column(String, primary_key=True)
    dbu_per_hour = Column(Float)
    min_clusters = Column(Integer)
    max_clusters = Column(Integer)
