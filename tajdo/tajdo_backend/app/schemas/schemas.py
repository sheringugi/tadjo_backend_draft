from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str = "customer"
    locale: str = "en"

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    locale: Optional[str] = None

class User(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Product Schemas
class ProductBase(BaseModel):
    sku: Optional[str] = None
    name: str
    description: Optional[str] = None
    price: Decimal
    original_price: Optional[Decimal] = None
    category_id: str
    image_url: Optional[str] = None
    badge: Optional[str] = None
    material: Optional[str] = None
    color: Optional[str] = None
    in_stock: bool = True
    shipping_days: int = 5

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: UUID
    rating: Decimal
    review_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Category Schemas
class CategoryBase(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    sort_order: int = 0

class Category(CategoryBase):
    created_at: datetime

    class Config:
        from_attributes = True

# Order Schemas
class OrderItemBase(BaseModel):
    product_id: UUID
    quantity: int

class OrderItem(OrderItemBase):
    id: UUID
    product_name: str
    unit_price: Decimal
    total: Decimal

    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    shipping_address_id: Optional[UUID] = None
    notes: Optional[str] = None
    payment_method: Optional[str] = None

class OrderCreate(OrderBase):
    items: List[OrderItemBase]

class Order(OrderBase):
    id: UUID
    order_number: str
    user_id: UUID
    status: str
    subtotal: Decimal
    shipping_cost: Decimal
    tax: Decimal
    total: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime
    items: List[OrderItem]

    class Config:
        from_attributes = True
