from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
DATABASE_URL = "postgresql+psycopg2://postgres:newpass123@localhost:5432/helpdesk_db"
engine=create_engine(DATABASE_URL)
sessionLocal=sessionmaker(autocommit=False, autoflush=False,bind=engine)
Base=declarative_base()
def get_db():
    db=sessionLocal()
    try:
        yield db
    finally:
        db.close()
             