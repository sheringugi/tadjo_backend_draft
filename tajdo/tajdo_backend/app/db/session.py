from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# For local development, ensure this is the "External URL" from your database provider (e.g., Render).
# Internal URLs (e.g., starting with 'dpg-') will not work from your local machine.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://tajdo_shop_db_0l4z_user:ury4LCAsW1iFuX3oqN0TX4q1cdvZKjB5@dpg-d711dc7kijhs73c9gd80-a.oregon-postgres.render.com/tajdo_shop_db_0l4z")

# SQLAlchemy 1.4+ requires 'postgresql://', but Render/Heroku often provide 'postgres://'
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
