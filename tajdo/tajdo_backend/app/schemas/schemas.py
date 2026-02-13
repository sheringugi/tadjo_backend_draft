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

# ProductSpecification Schemas (Moved up for nested creation)
class ProductSpecificationBase(BaseModel):
    product_id: Optional[UUID] = None
    spec: str

class ProductSpecificationCreate(ProductSpecificationBase):
    pass

class ProductSpecification(ProductSpecificationBase):
    id: UUID

    class Config:
        from_attributes = True

# ProductImage Schemas (Moved up for nested creation)
class ProductImageBase(BaseModel):
    product_id: Optional[UUID] = None
    url: str
    alt_text: Optional[str] = None
    sort_order: int = 0

class ProductImageCreate(ProductImageBase):
    pass

class ProductImage(ProductImageBase):
    id: UUID

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
    group_id: Optional[UUID] = None
    in_stock: bool = True
    shipping_days: int = 5

class ProductCreate(ProductBase):
    specifications: Optional[List[ProductSpecificationCreate]] = []
    images: Optional[List[ProductImageCreate]] = []

class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    category_id: Optional[str] = None
    image_url: Optional[str] = None
    badge: Optional[str] = None
    material: Optional[str] = None
    color: Optional[str] = None
    group_id: Optional[UUID] = None
    in_stock: Optional[bool] = None
    shipping_days: Optional[int] = None

class Product(ProductBase):
    id: UUID
    rating: Decimal
    review_count: int
    created_at: datetime
    updated_at: datetime
    specifications: List[ProductSpecification] = []
    images: List[ProductImage] = []

    class Config:
        from_attributes = True

# Category Schemas
class CategoryBase(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    sort_order: int = 0

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None

class Category(CategoryBase):
    created_at: datetime

    class Config:
        from_attributes = True

# Address Schemas
class AddressBase(BaseModel):
    label: str = "Home"
    line1: str
    line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str = "CH"
    is_default: bool = False

class AddressCreate(AddressBase):
    user_id: UUID

class Address(AddressBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# Wishlist Schemas
class WishlistBase(BaseModel):
    product_id: UUID

class Wishlist(WishlistBase):
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# CartItem Schemas
class CartItemBase(BaseModel):
    product_id: UUID
    quantity: int = 1

class CartItemCreate(CartItemBase):
    user_id: UUID

class CartItemUpdate(BaseModel):
    quantity: int

class CartItem(CartItemBase):
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# Order Schemas
class OrderItemBase(BaseModel):
    product_id: UUID
    quantity: int

class OrderItemCreate(OrderItemBase):
    pass

class OrderItem(OrderItemBase):
    id: UUID
    product_name: str
    unit_price: Decimal
    total: Decimal

    class Config:
        from_attributes = True

class CardDetails(BaseModel):
    card_number: str
    exp_month: int
    exp_year: int
    cvc: str
    card_holder_name: Optional[str] = None

class OrderBase(BaseModel):
    shipping_address_id: Optional[UUID] = None
    notes: Optional[str] = None
    payment_method: Optional[str] = None

class OrderCreate(OrderBase):
    user_id: UUID
    items: List[OrderItemCreate]
    card_details: Optional[CardDetails] = None # For card payments
    # Twint payment typically involves a redirect and callback, 
    # so direct details here might not be applicable for initial creation.
    # We'll assume a payment_method of 'twint' implies a pre-arranged flow or a placeholder.


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
    tracking_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[OrderItem]

    class Config:
        from_attributes = True

# OrderStatusHistory Schemas
class OrderStatusHistoryBase(BaseModel):
    order_id: UUID
    old_status: Optional[str] = None
    new_status: str
    note: Optional[str] = None

class OrderStatusHistoryCreate(OrderStatusHistoryBase):
    pass

class OrderStatusHistory(OrderStatusHistoryBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# Notification Schemas
class NotificationBase(BaseModel):
    user_id: UUID
    order_id: Optional[UUID] = None
    type: str
    title: str
    message: str
    is_read: bool = False

class NotificationCreate(NotificationBase):
    pass

class Notification(NotificationBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# Supplier Schemas
class SupplierBase(BaseModel):
    id: str
    name: str
    type: str
    location: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    default_lead_time: int = 14
    notes: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class Supplier(SupplierBase):
    created_at: datetime

    class Config:
        from_attributes = True

# SupplierOrder Schemas
class SupplierOrderBase(BaseModel):
    order_number: str
    supplier_id: str
    customer_order_id: Optional[UUID] = None
    status: str = "pending"
    total_cost: Decimal = 0
    currency: str = "USD"
    estimated_delivery_days: int = 14
    tracking_number: Optional[str] = None
    notes: Optional[str] = None

class SupplierOrderCreate(SupplierOrderBase):
    pass

class SupplierOrder(SupplierOrderBase):
    id: UUID
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    in_production_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    received_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# SupplierOrderItem Schemas
class SupplierOrderItemBase(BaseModel):
    supplier_order_id: UUID
    product_id: UUID
    product_name: str
    quantity: int
    unit_cost: Decimal = 0

class SupplierOrderItemCreate(SupplierOrderItemBase):
    pass

class SupplierOrderItem(SupplierOrderItemBase):
    id: UUID

    class Config:
        from_attributes = True

# SupplierPayment Schemas
class SupplierPaymentBase(BaseModel):
    supplier_id: str
    supplier_order_id: Optional[UUID] = None
    amount: Decimal
    currency: str = "USD"
    method: Optional[str] = None
    reference: Optional[str] = None

class SupplierPaymentCreate(SupplierPaymentBase):
    pass

class SupplierPayment(SupplierPaymentBase):
    id: UUID
    paid_at: datetime

    class Config:
        from_attributes = True

# Complaint Schemas
class ComplaintBase(BaseModel):
    user_id: UUID
    order_id: Optional[UUID] = None
    subject: str
    message: str
    status: str = "open"
    resolution: Optional[str] = None

class ComplaintCreate(ComplaintBase):
    pass

class Complaint(ComplaintBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Return Schemas
class ReturnBase(BaseModel):
    order_id: UUID
    user_id: UUID
    reason: str
    status: str = "requested"
    refund_amount: Optional[Decimal] = None
    notes: Optional[str] = None

class ReturnCreate(ReturnBase):
    pass

class Return(ReturnBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Review Schemas
class ReviewBase(BaseModel):
    product_id: UUID
    user_id: UUID
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = None
    body: Optional[str] = None

class ReviewCreate(ReviewBase):
    pass

class Review(ReviewBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# RescueContribution Schemas
class RescueContributionBase(BaseModel):
    order_id: UUID
    amount: Decimal
    currency: str = "CHF"

class RescueContributionCreate(RescueContributionBase):
    pass

class RescueContribution(RescueContributionBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class TokenData(BaseModel):
    email: Optional[str] = None
