from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
from .services.payment_service import process_twint_payment, process_card_payment
from datetime import timedelta

from .db.session import engine, Base, get_db
from .models import models
from .schemas import schemas
from .core.security import verify_password, get_password_hash, create_access_token, decode_access_token

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tajdo Online Store API", version="1.0.0")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

@app.get("/")
def read_root():
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
    return {"access_token": access_token, "token_type": "bearer"}

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

# User Endpoints
@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        password_hash=hashed_password,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        locale=user.locale
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/me/", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    return current_user

# Address Endpoints
@app.post("/addresses/", response_model=schemas.Address)
def create_address(address: schemas.AddressCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(address.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to create address for this user")
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
def update_cart_item(product_id: UUID, cart_item: schemas.CartItemBase, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    db_cart_item = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id,
        models.CartItem.product_id == product_id
    ).first()
    if db_cart_item is None:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    db_cart_item.quantity = cart_item.quantity
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
    subtotal = Decimal(0)
    order_items = []
    for item in order.items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ID {item.product_id} not found")
        
        item_total = product.price * item.quantity
        subtotal += item_total
        order_items.append(models.OrderItem(
            product_id=item.product_id,
            product_name=product.name,
            unit_price=product.price,
            quantity=item.quantity,
            total=item_total
        ))
    
    shipping_cost = Decimal(0) # Placeholder
    tax = subtotal * Decimal(0.08) # Assuming 8% tax
    total = subtotal + shipping_cost + tax

    db_order = models.Order(
        order_number=f"ORD-{uuid.uuid4().hex[:6].upper()}",
        user_id=order.user_id,
        shipping_address_id=order.shipping_address_id,
        status="pending",
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        tax=tax,
        total=total,
        currency="CHF",
    payment_method=order.payment_method,
    payment_intent_id=None, # Will be updated after payment processing
    notes=order.notes,
    items=order_items

    )
    # Process payment based on method
    if order.payment_method == "twint":
        payment_result = process_twint_payment(float(total), db_order.currency)
    elif order.payment_method == "card" and order.card_details:
        payment_result = process_card_payment(float(total), db_order.currency, order.card_details.dict())
    else:
        # For other payment methods or if card details are missing for card payment,
        # we can assume payment will be handled externally or is not required at this stage.
        # For now, we'll just set status to pending and proceed.
        payment_result = {"status": "pending", "transaction_id": None}

    if payment_result["status"] == "succeeded":
        db_order.status = "confirmed"
        db_order.payment_intent_id = payment_result["transaction_id"]
    elif payment_result["status"] == "failed":
        db_order.status = "cancelled" # Or a specific 'payment_failed' status
        raise HTTPException(status_code=400, detail=f"Payment failed: {payment_result.get('error', 'Unknown error')}")
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@app.get("/orders/{order_id}", response_model=schemas.Order)
def read_order(order_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if str(db_order.user_id) != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    return db_order

@app.get("/users/{user_id}/orders/", response_model=List[schemas.Order])
def read_user_orders(user_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(user_id) != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view orders for this user")
    orders = db.query(models.Order).filter(models.Order.user_id == user_id).all()
    return orders

@app.put("/orders/{order_id}/status", response_model=schemas.Order)
def update_order_status(order_id: UUID, new_status: str, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update order status")
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
    db.commit()
    db.refresh(db_order)
    return db_order

# Product Specification Endpoints
@app.post("/products/{product_id}/specifications/", response_model=schemas.ProductSpecification)
def create_product_specification(product_id: UUID, spec: schemas.ProductSpecificationCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can add product specifications")
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
def create_product_image(product_id: UUID, image: schemas.ProductImageCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can add product images")
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
def create_supplier(supplier: schemas.SupplierCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create suppliers")
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
def create_supplier_order(supplier_order: schemas.SupplierOrderCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create supplier orders")
    db_supplier_order = models.SupplierOrder(**supplier_order.dict())
    db.add(db_supplier_order)
    db.commit()
    db.refresh(db_supplier_order)
    return db_supplier_order

@app.get("/supplier_orders/", response_model=List[schemas.SupplierOrder])
def read_supplier_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view supplier orders")
    supplier_orders = db.query(models.SupplierOrder).offset(skip).limit(limit).all()
    return supplier_orders

@app.get("/supplier_orders/{order_id}", response_model=schemas.SupplierOrder)
def read_supplier_order(order_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view supplier orders")
    db_supplier_order = db.query(models.SupplierOrder).filter(models.SupplierOrder.id == order_id).first()
    if db_supplier_order is None:
        raise HTTPException(status_code=404, detail="Supplier Order not found")
    return db_supplier_order

# Supplier Order Item Endpoints
@app.post("/supplier_order_items/", response_model=schemas.SupplierOrderItem)
def create_supplier_order_item(item: schemas.SupplierOrderItemCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create supplier order items")
    db_item = models.SupplierOrderItem(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/supplier_orders/{order_id}/items/", response_model=List[schemas.SupplierOrderItem])
def read_supplier_order_items(order_id: UUID, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view supplier order items")
    items = db.query(models.SupplierOrderItem).filter(models.SupplierOrderItem.supplier_order_id == order_id).all()
    return items

# Supplier Payment Endpoints
@app.post("/supplier_payments/", response_model=schemas.SupplierPayment)
def create_supplier_payment(payment: schemas.SupplierPaymentCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create supplier payments")
    db_payment = models.SupplierPayment(**payment.dict())
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

@app.get("/suppliers/{supplier_id}/payments/", response_model=List[schemas.SupplierPayment])
def read_supplier_payments(supplier_id: str, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view supplier payments")
    payments = db.query(models.SupplierPayment).filter(models.SupplierPayment.supplier_id == supplier_id).all()
    return payments

# Complaint Endpoints
@app.post("/complaints/", response_model=schemas.Complaint)
def create_complaint(complaint: schemas.ComplaintCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(complaint.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to create complaint for this user")
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
@app.post("/returns/", response_model=schemas.Return)
def create_return(return_request: schemas.ReturnCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(return_request.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to create return for this user")
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
@app.post("/reviews/", response_model=schemas.Review)
def create_review(review: schemas.ReviewCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    if str(review.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to create review for this user")
    db_review = models.Review(**review.dict())
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

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
