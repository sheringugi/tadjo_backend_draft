from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .db.session import engine, Base, get_db
from .models import models
from .schemas import schemas

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tajdo Online Store API", version="1.0.0")

@app.get("/")
def read_root():
    return {"message": "Welcome to Tajdo Online Store API"}

# Product Endpoints
@app.get("/products/", response_model=List[schemas.Product])
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    products = db.query(models.Product).offset(skip).limit(limit).all()
    return products

@app.get("/products/{product_id}", response_model=schemas.Product)
def read_product(product_id: str, db: Session = Depends(get_db)):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

# Category Endpoints
@app.get("/categories/", response_model=List[schemas.Category])
def read_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).all()

# User Endpoints (Simplified for now)
@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # In a real application, you would hash the password here
    # For example, using passlib:
    # from passlib.context import CryptContext
    # pwd_context = CryptContext(schemes=['bcrypt'], deprecated="auto")
    # hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        email=user.email,
        password_hash=user.password, # Replace with hashed_password
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        locale=user.locale
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
