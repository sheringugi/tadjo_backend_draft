from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
import uuid
# from .services.payment_service import process_twint_payment, process_card_payment
from datetime import timedelta

from .db.session import engine, Base, get_db
from .models import models
from .schemas import schemas
from .core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from .core.config import settings
from .dependencies import get_current_user, get_current_admin
from .services.email_service import EmailService
from app.routers import payments


email_service = EmailService()

# Create database tables
# This is handled by Alembic migrations. It's good practice to not have this in the main app.
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tajdo Online Store API", version="1.0.0")

# include routers for payment through stripe
app.include_router(payments.router)
# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_origin_regex=r"https://tadjo-frontend.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/")
def read_root():
    print("Root endpoint accessed!")
    return {"message": "Welcome to Tajdo Online Store API"}

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

@app.post("/auth/admin/login", response_model=schemas.Token)
async def admin_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access admin portal")
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email, "role": "admin"}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

# Product Endpoints
@app.get("/products/", response_model=List[schemas.Product])
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    products = db.query(models.Product).offset(skip).limit(limit).all()
    
    # Calculate average rating and review count efficiently
    product_ids = [p.id for p in products]
    reviews = db.query(models.Review).filter(models.Review.product_id.in_(product_ids)).all()
    
    reviews_map = {}
    for r in reviews:
        if r.product_id not in reviews_map:
            reviews_map[r.product_id] = []
        reviews_map[r.product_id].append(r)
        
    for product in products:
        product_reviews = reviews_map.get(product.id, [])
        if product_reviews:
            avg_rating = sum(r.rating for r in product_reviews) / len(product_reviews)
            product.rating = Decimal(avg_rating)
            product.review_count = len(product_reviews)
        else:
            product.rating = Decimal(0)
            product.review_count = 0
            
    return products

@app.post("/products/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    # Create the product

    # Validate that the category exists
    category = db.query(models.Category).filter(models.Category.id == product.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail=f"Category with id '{product.category_id}' not found.")

    product_data = product.dict(exclude={'specifications', 'images'})
    db_product = models.Product(**product_data)
    db.add(db_product)
    db.flush() # Flush to get the product ID before creating related items

    # Create nested specifications
    if product.specifications:
        for spec in product.specifications:
            db_spec = models.ProductSpecification(product_id=db_product.id, spec=spec.spec)
            db.add(db_spec)

    # Create nested images
    if product.images:
        for image in product.images:
            db_image = models.ProductImage(
                product_id=db_product.id, 
                url=image.url, 
                alt_text=image.alt_text, 
                sort_order=image.sort_order
            )
            db.add(db_image)

    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products/{product_id}", response_model=schemas.Product)
def read_product(product_id: UUID, db: Session = Depends(get_db)):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Calculate rating
    reviews = db.query(models.Review).filter(models.Review.product_id == product_id).all()
    if reviews:
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
        db_product.rating = Decimal(avg_rating)
        db_product.review_count = len(reviews)
    else:
        db_product.rating = Decimal(0)
        db_product.review_count = 0
        
    return db_product

@app.put("/products/{product_id}", response_model=schemas.Product)
def update_product(product_id: UUID, product_update: schemas.ProductUpdate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
    
    db.commit()
    db.refresh(db_product)
    return db_product

# Category Endpoints
@app.get("/categories/", response_model=List[schemas.Category])
def read_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).all()

@app.post("/categories/", response_model=schemas.Category)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    db_category = models.Category(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@app.put("/categories/{category_id}", response_model=schemas.Category)
def update_category(category_id: str, category_update: schemas.CategoryUpdate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = category_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_category, key, value)
    
    db.commit()
    db.refresh(db_category)
    return db_category

@app.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: str, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(db_category)
    db.commit()
    return

# User Endpoints
@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = db.query(models.User).filter(models.User.email == user.email).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        if len(user.password.encode('utf-8')) > 72:
            raise HTTPException(status_code=400, detail="Password is too long. Maximum length is 72 bytes.")

        hashed_password = get_password_hash(user.password)
        db_user = models.User(
            email=user.email,
            password_hash=hashed_password,
            full_name=user.full_name,
            phone=user.phone,
            role="customer", # Force customer role for public registration
            locale=user.locale
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        print(f"CRITICAL ERROR creating user: {e}")
        if "password cannot be longer than 72 bytes" in str(e):
            raise HTTPException(status_code=400, detail="Password is too long. Maximum length is 72 bytes.")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/users/me/", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    return current_user

# Address Endpoints
@app.post("/addresses/", response_model=schemas.Address)
def create_address(address: schemas.AddressCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(address.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to create address for this user")
    
    # If the new address is set as default, unset is_default for all other addresses of this user
    if address.is_default:
        db.query(models.Address).filter(models.Address.user_id == address.user_id).update({"is_default": False})

    db_address = models.Address(**address.dict())
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address

@app.get("/users/{user_id}/addresses/", response_model=List[schemas.Address])
def read_user_addresses(user_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view addresses for this user")
    addresses = db.query(models.Address).filter(models.Address.user_id == user_id).all()
    return addresses

# Wishlist Endpoints
@app.post("/wishlists/", response_model=schemas.Wishlist)
def add_to_wishlist(wishlist_item: schemas.WishlistBase, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    existing_item = db.query(models.Wishlist).filter(
        models.Wishlist.user_id == current_user.id,
        models.Wishlist.product_id == wishlist_item.product_id
    ).first()
    if existing_item:
        return existing_item

    db_wishlist_item = models.Wishlist(user_id=current_user.id, **wishlist_item.dict())
    db.add(db_wishlist_item)
    db.commit()
    db.refresh(db_wishlist_item)
    return db_wishlist_item

@app.get("/users/{user_id}/wishlist/", response_model=List[schemas.Product])
def read_user_wishlist(user_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view wishlist for this user")
    wishlist_products = db.query(models.Product).join(models.Wishlist).filter(models.Wishlist.user_id == user_id).all()
    return wishlist_products

@app.delete("/wishlists/", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_wishlist(wishlist_item: schemas.WishlistBase, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    db_wishlist_item = db.query(models.Wishlist).filter(
        models.Wishlist.user_id == current_user.id,
        models.Wishlist.product_id == wishlist_item.product_id
    ).first()
    if db_wishlist_item is None:
        raise HTTPException(status_code=404, detail="Item not found in wishlist")
    db.delete(db_wishlist_item)
    db.commit()
    return

# CartItem Endpoints
@app.post("/cart/items/", response_model=schemas.CartItem)
def add_to_cart(cart_item: schemas.CartItemBase, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    db_cart_item = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id,
        models.CartItem.product_id == cart_item.product_id
    ).first()
    if db_cart_item:
        db_cart_item.quantity += cart_item.quantity
    else:
        db_cart_item = models.CartItem(user_id=current_user.id, **cart_item.dict())
    db.add(db_cart_item)
    db.commit()
    db.refresh(db_cart_item)
    return db_cart_item

@app.get("/users/{user_id}/cart/items/", response_model=List[schemas.CartItem])
def read_user_cart_items(user_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view cart for this user")
    cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == user_id).all()
    return cart_items

@app.put("/cart/items/{product_id}", response_model=schemas.CartItem)
def update_cart_item(product_id: UUID, cart_item_update: schemas.CartItemUpdate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    db_cart_item = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id,
        models.CartItem.product_id == product_id
    ).first()
    if db_cart_item is None:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    db_cart_item.quantity = cart_item_update.quantity
    db.commit()
    db.refresh(db_cart_item)
    return db_cart_item

@app.delete("/cart/items/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_cart(product_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    db_cart_item = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id,
        models.CartItem.product_id == product_id
    ).first()
    if db_cart_item is None:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    db.delete(db_cart_item)
    db.commit()
    return

# Order Endpoints
@app.post("/orders/", response_model=schemas.Order)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(order.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to create order for this user")

    # Calculate subtotal, tax, total
    gross_total = Decimal(0)
    order_items = []
    for item in order.items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ID {item.product_id} not found")
        
        # In a Tax Inclusive model, the product price is the gross price
        item_total = product.price * item.quantity
        gross_total += item_total
        order_items.append(models.OrderItem(
            product_id=item.product_id,
            product_name=product.name,
            unit_price=product.price,
            quantity=item.quantity,
            total=item_total,
            manufacturing_cost=product.manufacturing_cost,
            transport_cost=product.transport_cost
        ))
    
    shipping_cost = Decimal(0) # DDP Shipping (Free to customer)
    
    # Tax Inclusive Calculation (Switzerland Standard Rate 8.1%)
    # Formula: Tax = Total - (Total / (1 + Rate))
    tax_rate = Decimal("0.081")
    total = gross_total + shipping_cost
    
    # Calculate the net amount (pre-tax)
    net_total = total / (1 + tax_rate)
    
    # Extract the tax amount
    tax = total - net_total
    
    # Subtotal in DB usually refers to pre-tax amount of items
    subtotal = net_total
    
    # Rounding to 2 decimal places for currency
    tax = tax.quantize(Decimal("0.01"))
    subtotal = subtotal.quantize(Decimal("0.01"))
    total = total.quantize(Decimal("0.01"))

    db_order = models.Order(
        order_number=f"ORD-{uuid.uuid4().hex[:6].upper()}",
        user_id=order.user_id,
        shipping_address_id=order.shipping_address_id,
        status="processing", # Payment is confirmed on frontend before calling this
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        tax=tax,
        total=total,
        currency="CHF",
        payment_method=order.payment_method,
        payment_intent_id=order.payment_intent_id, # Pass from frontend
        notes=order.notes,
        items=order_items
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # Clear ordered items from the cart
    for item in order.items:
        db.query(models.CartItem).filter(
            models.CartItem.user_id == current_user.id,
            models.CartItem.product_id == item.product_id
        ).delete()

    # Create Rescue Contribution (30% of total)
    rescue_amount = (total * Decimal("0.30")).quantize(Decimal("0.01"))
    db_rescue = models.RescueContribution(
        order_id=db_order.id,
        amount=rescue_amount,
        currency=db_order.currency
    )
    db.add(db_rescue)
    db.commit()

    # Create a notification for the user
    notification = models.Notification(
        user_id=db_order.user_id,
        order_id=db_order.id,
        type="order_confirmation",
        title="Order Confirmed",
        message=f"Thank you for your purchase! Your order {db_order.order_number} has been placed. We are preparing your order."
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # Send confirmation email
    try:
        email_service.send_order_confirmation(db_order, current_user)
    except Exception as e:
        print(f"Failed to send confirmation email: {e}")
        # Do not fail the order if email fails

    return db_order

@app.get("/admin/orders/", response_model=List[schemas.Order])
def read_all_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    orders = db.query(models.Order).offset(skip).limit(limit).all()
    return orders

@app.get("/orders/{order_id}", response_model=schemas.Order)
def read_order(order_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if str(db_order.user_id) != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    return db_order

@app.get("/orders/track")
async def track_order(
    order_number: str,
    email: str,
    db: Session = Depends(get_db)
):
    order = db.query(models.Order).filter(models.Order.order_number == order_number).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.user.email != email:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order

@app.get("/users/{user_id}/orders/", response_model=List[schemas.Order])
def read_user_orders(user_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(user_id) != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view orders for this user")
    orders = db.query(models.Order).filter(models.Order.user_id == user_id).all()
    return orders

@app.put("/orders/{order_id}/status", response_model=schemas.Order)
def update_order_status(order_id: UUID, new_status: str, tracking_number: Optional[str] = None, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Log status change
    status_history = models.OrderStatusHistory(
        order_id=db_order.id,
        old_status=db_order.status,
        new_status=new_status,
        note=f"Status updated by admin {current_user.full_name}"
    )
    db.add(status_history)

    db_order.status = new_status
    if tracking_number:
        db_order.tracking_number = tracking_number

    db.commit()
    db.refresh(db_order)

    # Determine notification message based on status
    title = f"Order {new_status.capitalize()}"
    message = f"The status of your order {db_order.order_number} has been updated to {new_status}."

    if new_status == "processing":
        message = f"We are preparing your order {db_order.order_number}."
    elif new_status == "shipped":
        title = "Order Shipped"
        message = f"Great news! Your order {db_order.order_number} is on its way."
        if tracking_number:
            message += f" Tracking Number: {tracking_number}"
    elif new_status == "delivered":
        title = "Order Delivered"
        message = f"Your order {db_order.order_number} has arrived! We hope you love your new items."
    elif new_status == "cancelled":
        title = "Order Cancelled"
        message = f"Your order {db_order.order_number} has been cancelled. If you have questions, please contact us."
    elif new_status == "refunded":
        title = "Order Refunded"
        message = f"A refund has been processed for your order {db_order.order_number}."

    # Create a notification for the status update
    notification = models.Notification(
        user_id=db_order.user_id,
        order_id=db_order.id,
        type="order_status_update",
        title=title,
        message=message
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # Send email notification for status update
    try:
        if new_status == "shipped":
            email_service.send_order_shipped(db_order, db_order.user, tracking_number)
        elif new_status == "delivered":
            email_service.send_order_delivered(db_order, db_order.user)
        elif new_status == "cancelled":
            email_service.send_order_cancelled(db_order, db_order.user)
        elif new_status == "refunded":
            email_service.send_order_refunded(db_order, db_order.user)
    except Exception as e:
        print(f"Failed to send status update email: {e}")

    return db_order

# Product Specification Endpoints
@app.post("/products/{product_id}/specifications/", response_model=schemas.ProductSpecification)
def create_product_specification(product_id: UUID, spec: schemas.ProductSpecificationCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    db_spec = models.ProductSpecification(product_id=product_id, spec=spec.spec)
    db.add(db_spec)
    db.commit()
    db.refresh(db_spec)
    return db_spec

@app.get("/products/{product_id}/specifications/", response_model=List[schemas.ProductSpecification])
def read_product_specifications(product_id: UUID, db: Session = Depends(get_db)):
    specs = db.query(models.ProductSpecification).filter(models.ProductSpecification.product_id == product_id).all()
    return specs

# Product Image Endpoints
@app.post("/products/{product_id}/images/", response_model=schemas.ProductImage)
def create_product_image(product_id: UUID, image: schemas.ProductImageCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    db_image = models.ProductImage(product_id=product_id, url=image.url, alt_text=image.alt_text, sort_order=image.sort_order)
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image

@app.get("/products/{product_id}/images/", response_model=List[schemas.ProductImage])
def read_product_images(product_id: UUID, db: Session = Depends(get_db)):
    images = db.query(models.ProductImage).filter(models.ProductImage.product_id == product_id).all()
    return images

# Notification Endpoints
@app.post("/notifications/", response_model=schemas.Notification)
def create_notification(notification: schemas.NotificationCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(notification.user_id) != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to create notification for this user")
    
    if notification.order_id:
        db_order = db.query(models.Order).filter(models.Order.id == notification.order_id).first()
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        if str(db_order.user_id) != str(notification.user_id):
            raise HTTPException(status_code=400, detail="Notification user_id does not match the order's user_id")
            
    db_notification = models.Notification(**notification.dict())
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

@app.get("/users/{user_id}/notifications/", response_model=List[schemas.Notification])
def read_user_notifications(user_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(user_id) != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view notifications for this user")
    notifications = db.query(models.Notification).filter(models.Notification.user_id == user_id).all()
    return notifications

@app.put("/notifications/{notification_id}/read", response_model=schemas.Notification)
def mark_notification_as_read(notification_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    db_notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if db_notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if str(db_notification.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to mark this notification as read")
    db_notification.is_read = True
    db.commit()
    db.refresh(db_notification)
    return db_notification

# Supplier Endpoints
@app.post("/suppliers/", response_model=schemas.Supplier)
def create_supplier(supplier: schemas.SupplierCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    db_supplier = models.Supplier(**supplier.dict())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

@app.get("/suppliers/", response_model=List[schemas.Supplier])
def read_suppliers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    suppliers = db.query(models.Supplier).offset(skip).limit(limit).all()
    return suppliers

@app.get("/suppliers/{supplier_id}", response_model=schemas.Supplier)
def read_supplier(supplier_id: str, db: Session = Depends(get_db)):
    db_supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if db_supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return db_supplier

# Supplier Order Endpoints
@app.post("/supplier_orders/", response_model=schemas.SupplierOrder)
def create_supplier_order(supplier_order: schemas.SupplierOrderCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    db_supplier_order = models.SupplierOrder(**supplier_order.dict())
    db.add(db_supplier_order)
    db.commit()
    db.refresh(db_supplier_order)
    return db_supplier_order

@app.get("/supplier_orders/", response_model=List[schemas.SupplierOrder])
def read_supplier_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    supplier_orders = db.query(models.SupplierOrder).offset(skip).limit(limit).all()
    return supplier_orders

@app.get("/supplier_orders/{order_id}", response_model=schemas.SupplierOrder)
def read_supplier_order(order_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    db_supplier_order = db.query(models.SupplierOrder).filter(models.SupplierOrder.id == order_id).first()
    if db_supplier_order is None:
        raise HTTPException(status_code=404, detail="Supplier Order not found")
    return db_supplier_order

# Supplier Order Item Endpoints
@app.post("/supplier_order_items/", response_model=schemas.SupplierOrderItem)
def create_supplier_order_item(item: schemas.SupplierOrderItemCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    db_item = models.SupplierOrderItem(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/supplier_orders/{order_id}/items/", response_model=List[schemas.SupplierOrderItem])
def read_supplier_order_items(order_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    items = db.query(models.SupplierOrderItem).filter(models.SupplierOrderItem.supplier_order_id == order_id).all()
    return items

# Supplier Payment Endpoints
@app.post("/supplier_payments/", response_model=schemas.SupplierPayment)
def create_supplier_payment(payment: schemas.SupplierPaymentCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    db_payment = models.SupplierPayment(**payment.dict())
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

@app.get("/suppliers/{supplier_id}/payments/", response_model=List[schemas.SupplierPayment])
def read_supplier_payments(supplier_id: str, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    payments = db.query(models.SupplierPayment).filter(models.SupplierPayment.supplier_id == supplier_id).all()
    return payments

# Complaint Endpoints
@app.get("/admin/complaints/", response_model=List[schemas.Complaint])
def read_all_complaints(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    complaints = db.query(models.Complaint).offset(skip).limit(limit).all()
    return complaints

@app.post("/complaints/", response_model=schemas.Complaint)
def create_complaint(complaint: schemas.ComplaintCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(complaint.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to create complaint for this user")
    
    if complaint.order_id:
        db_order = db.query(models.Order).filter(models.Order.id == complaint.order_id).first()
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        if str(db_order.user_id) != str(complaint.user_id):
            raise HTTPException(status_code=400, detail="Complaint user_id does not match the order's user_id")
            
    db_complaint = models.Complaint(**complaint.dict())
    db.add(db_complaint)
    db.commit()
    db.refresh(db_complaint)
    return db_complaint

@app.get("/users/{user_id}/complaints/", response_model=List[schemas.Complaint])
def read_user_complaints(user_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(user_id) != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view complaints for this user")
    complaints = db.query(models.Complaint).filter(models.Complaint.user_id == user_id).all()
    return complaints

# Return Endpoints
@app.get("/admin/returns/", response_model=List[schemas.Return])
def read_all_returns(skip: int =0, limit: int =100, db: Session = Depends (get_db), current_user: schemas.User = Depends(get_current_admin)):
    returns = db.query(models.Return).offset(skip).limit(limit).all()
    return returns

@app.post("/returns/", response_model=schemas.Return)
def create_return(return_request: schemas.ReturnCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(return_request.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to create return for this user")
    
    db_order = db.query(models.Order).filter(models.Order.id == return_request.order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    if str(db_order.user_id) != str(return_request.user_id):
        raise HTTPException(status_code=400, detail="Return user_id does not match the order's user_id")

    db_return = models.Return(**return_request.dict())
    db.add(db_return)
    db.commit()
    db.refresh(db_return)
    return db_return

@app.get("/users/{user_id}/returns/", response_model=List[schemas.Return])
def read_user_returns(user_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(user_id) != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view returns for this user")
    returns = db.query(models.Return).filter(models.Return.user_id == user_id).all()
    return returns

# Review Endpoints
@app.get("/admin/reviews/", response_model=List[schemas.Review])
def read_all_reviews(skip: int =0, limit: int =100, db: Session = Depends (get_db), current_user: schemas.User = Depends(get_current_admin)):
    reviews = db.query(models.Review).offset(skip).limit(limit).all()
    return reviews

@app.post("/reviews/", response_model=schemas.Review)
def create_review(review: schemas.ReviewCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(review.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to create review for this user")
    
    if not db.query(models.Product).filter(models.Product.id == review.product_id).first():
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if user has purchased the product
    has_purchased = db.query(models.OrderItem).join(models.Order).filter(
        models.Order.user_id == current_user.id,
        models.OrderItem.product_id == review.product_id
    ).first()
    if not has_purchased:
        raise HTTPException(status_code=403, detail="You must purchase this product to review it")

    db_review = models.Review(**review.dict())
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

@app.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    db_review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")
    db.delete(db_review)
    db.commit()
    return

@app.get("/products/{product_id}/reviews/", response_model=List[schemas.Review])
def read_product_reviews(product_id: UUID, db: Session = Depends(get_db)):
    reviews = db.query(models.Review).filter(models.Review.product_id == product_id).all()
    return reviews

# Rescue Contribution Endpoints
@app.get("/orders/{order_id}/rescue_contribution/", response_model=schemas.RescueContribution)
def read_rescue_contribution(order_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    db_contribution = db.query(models.RescueContribution).filter(models.RescueContribution.order_id == order_id).first()
    if db_contribution is None:
        raise HTTPException(status_code=404, detail="Rescue contribution not found for this order")
    # Only allow admin or the user who placed the order to view
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if order and (str(order.user_id) == str(current_user.id) or current_user.role == "admin"):
        return db_contribution
    raise HTTPException(status_code=403, detail="Not authorized to view this rescue contribution")

@app.get("/admin/rescue-contributions/", response_model=List[schemas.RescueContribution])
def read_all_rescue_contributions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_admin)):
    contributions = db.query(models.RescueContribution).offset(skip).limit(limit).all()
    return contributions
