from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
import uuid
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Database Setup ─────────────────────────────────────────────────────────────
DATABASE_URL = "sqlite:///./nexusstore.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ── Email Config ───────────────────────────────────────────────────────────────
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SENDER_EMAIL  = "damilareadebayo27@gmail.com"
SENDER_PASS   = "jfawjvdntewkoxzl"
ADMIN_EMAIL   = "damilareadebayo27@gmail.com"

# ── DB Models ──────────────────────────────────────────────────────────────────
class ProductDB(Base):
    __tablename__ = "products"
    id    = Column(Integer, primary_key=True, index=True)
    name  = Column(String)
    sub   = Column(String)
    price = Column(Float)
    icon  = Column(String)
    tag   = Column(String, nullable=True)
    cat   = Column(String)

class UserDB(Base):
    __tablename__ = "users"
    id       = Column(Integer, primary_key=True, index=True)
    name     = Column(String)
    email    = Column(String, unique=True, index=True)
    password = Column(String)
    orders   = relationship("OrderDB", back_populates="user")

class CartDB(Base):
    __tablename__ = "carts"
    id    = Column(String, primary_key=True)
    items = relationship("CartItemDB", back_populates="cart")

class CartItemDB(Base):
    __tablename__ = "cart_items"
    id         = Column(Integer, primary_key=True, index=True)
    cart_id    = Column(String, ForeignKey("carts.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity   = Column(Integer, default=1)
    cart       = relationship("CartDB", back_populates="items")
    product    = relationship("ProductDB")

class OrderDB(Base):
    __tablename__ = "orders"
    id         = Column(String, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    name       = Column(String)
    email      = Column(String)
    address    = Column(String)
    total      = Column(Float)
    status     = Column(String, default="confirmed")
    created_at = Column(DateTime, default=datetime.utcnow)
    items      = relationship("OrderItemDB", back_populates="order")
    user       = relationship("UserDB", back_populates="orders")

class OrderItemDB(Base):
    __tablename__ = "order_items"
    id         = Column(Integer, primary_key=True, index=True)
    order_id   = Column(String, ForeignKey("orders.id"))
    product_id = Column(Integer)
    name       = Column(String)
    icon       = Column(String)
    price      = Column(Float)
    quantity   = Column(Integer)
    order      = relationship("OrderDB", back_populates="items")

Base.metadata.create_all(bind=engine)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Seed ───────────────────────────────────────────────────────────────────────
def seed_products(db: Session):
    if db.query(ProductDB).count() == 0:
        db.add_all([
            ProductDB(name="NX-Vision Pro",    sub="AR Headset",     price=1299, icon="🥽", tag="New",  cat="Wearables"),
            ProductDB(name="SoundCore X9",     sub="Spatial Audio",  price=349,  icon="🎧", tag="Hot",  cat="Audio"),
            ProductDB(name="PulseWatch Ultra", sub="Biosensor OS",   price=599,  icon="⌚", tag="Sale", cat="Wearables"),
            ProductDB(name="ProPad Z1",        sub="Haptic Tablet",  price=799,  icon="📱", tag="New",  cat="Computing"),
            ProductDB(name="AirBud Nano",      sub="Neural Fit",     price=199,  icon="🎵", tag="Hot",  cat="Audio"),
            ProductDB(name="NX Keypad",        sub="Mech Wireless",  price=249,  icon="⌨️", tag=None,   cat="Accessories"),
            ProductDB(name="HoloLink 3",       sub="Projection Hub", price=449,  icon="🔮", tag="New",  cat="Computing"),
            ProductDB(name="CoolGel Case",     sub="Phase Material", price=79,   icon="🛡️", tag=None,   cat="Accessories"),
        ])
        db.commit()

with SessionLocal() as db:
    seed_products(db)

# ── Email Helpers ──────────────────────────────────────────────────────────────
async def send_email(to: str, subject: str, html: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"NexusStore <{SENDER_EMAIL}>"
    msg["To"]      = to
    msg.attach(MIMEText(html, "html"))
    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            username=SENDER_EMAIL,
            password=SENDER_PASS,
        )
        print(f"✅ Email sent to {to}")
    except Exception as e:
        print(f"❌ Email error: {e}")


def user_email_html(order_id, name, address, items, total):
    rows = "".join(
        f"<tr><td style='padding:10px;border-bottom:1px solid #1a2235;font-size:20px'>{i['icon']}</td>"
        f"<td style='padding:10px;border-bottom:1px solid #1a2235;color:#E8EAF0'>{i['name']}</td>"
        f"<td style='padding:10px;border-bottom:1px solid #1a2235;color:#5A6380'>x{i['quantity']}</td>"
        f"<td style='padding:10px;border-bottom:1px solid #1a2235;color:#00FFD1;font-family:monospace'>${i['price'] * i['quantity']:,.0f}</td></tr>"
        for i in items
    )
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#080B12;font-family:'Helvetica Neue',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#080B12;padding:40px 0;">
    <tr><td align="center">
      <table width="580" cellpadding="0" cellspacing="0" style="background:#0E1420;border:1px solid rgba(0,255,209,0.12);border-radius:12px;overflow:hidden;">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#0E1420,#141B2D);padding:36px 40px;border-bottom:1px solid rgba(0,255,209,0.12);">
          <p style="margin:0;font-size:22px;font-weight:800;color:#00FFD1;letter-spacing:-0.5px;">NEXUS<span style="color:#E8EAF0">STORE</span></p>
          <p style="margin:8px 0 0;font-size:13px;color:#5A6380;font-family:monospace;letter-spacing:1px;">// ORDER CONFIRMED</p>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:36px 40px;">
          <p style="font-size:28px;margin:0 0 6px;font-weight:800;color:#E8EAF0;">🎉 Thank you, {name.split()[0]}!</p>
          <p style="color:#5A6380;font-size:14px;line-height:1.7;margin:0 0 28px;">Your order has been confirmed and is being prepared for delivery. We'll notify you once it ships.</p>

          <div style="background:#141B2D;border:1px solid rgba(0,255,209,0.12);border-radius:8px;padding:20px;margin-bottom:24px;">
            <p style="margin:0 0 4px;font-size:11px;color:#5A6380;font-family:monospace;letter-spacing:2px;text-transform:uppercase;">Order ID</p>
            <p style="margin:0;font-size:26px;font-weight:800;color:#00FFD1;font-family:monospace;">#{order_id}</p>
          </div>

          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
            <tr style="background:#141B2D;">
              <th style="padding:10px;text-align:left;font-size:10px;color:#5A6380;letter-spacing:1px;text-transform:uppercase;font-weight:500;border-bottom:1px solid rgba(0,255,209,0.12);" colspan="2">Product</th>
              <th style="padding:10px;text-align:left;font-size:10px;color:#5A6380;letter-spacing:1px;text-transform:uppercase;font-weight:500;border-bottom:1px solid rgba(0,255,209,0.12);">Qty</th>
              <th style="padding:10px;text-align:left;font-size:10px;color:#5A6380;letter-spacing:1px;text-transform:uppercase;font-weight:500;border-bottom:1px solid rgba(0,255,209,0.12);">Price</th>
            </tr>
            {rows}
          </table>

          <div style="display:flex;justify-content:space-between;padding:16px 20px;background:#141B2D;border-radius:6px;margin-bottom:24px;">
            <span style="color:#5A6380;font-size:13px;">Order Total</span>
            <span style="color:#00FFD1;font-size:22px;font-weight:800;font-family:monospace;">${total:,.0f}</span>
          </div>

          <div style="background:#141B2D;border:1px solid rgba(0,255,209,0.12);border-radius:8px;padding:20px;margin-bottom:28px;">
            <p style="margin:0 0 6px;font-size:11px;color:#5A6380;font-family:monospace;letter-spacing:2px;text-transform:uppercase;">Delivery Address</p>
            <p style="margin:0;font-size:14px;color:#E8EAF0;line-height:1.6;">{address}</p>
          </div>

          <p style="color:#5A6380;font-size:13px;line-height:1.7;margin:0;">
            Expected delivery: <span style="color:#E8EAF0;font-weight:600;">Within 12 hours</span><br>
            Questions? Reply to this email or visit our <span style="color:#00FFD1;">Support page</span>.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:24px 40px;border-top:1px solid rgba(0,255,209,0.12);background:#080B12;">
          <p style="margin:0;font-size:12px;color:#5A6380;text-align:center;">© 2077 NexusStore · Built for the future · You're receiving this because you placed an order.</p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def admin_email_html(order_id, name, email, address, items, total):
    rows = "".join(
        f"<tr><td style='padding:10px;border-bottom:1px solid #1a2235;font-size:18px'>{i['icon']}</td>"
        f"<td style='padding:10px;border-bottom:1px solid #1a2235;color:#E8EAF0'>{i['name']}</td>"
        f"<td style='padding:10px;border-bottom:1px solid #1a2235;color:#5A6380'>x{i['quantity']}</td>"
        f"<td style='padding:10px;border-bottom:1px solid #1a2235;color:#00FFD1;font-family:monospace'>${i['price'] * i['quantity']:,.0f}</td></tr>"
        for i in items
    )
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#080B12;font-family:'Helvetica Neue',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#080B12;padding:40px 0;">
    <tr><td align="center">
      <table width="580" cellpadding="0" cellspacing="0" style="background:#0E1420;border:1px solid rgba(255,77,106,0.2);border-radius:12px;overflow:hidden;">

        <!-- Header -->
        <tr><td style="background:#141B2D;padding:28px 40px;border-bottom:1px solid rgba(255,77,106,0.15);">
          <p style="margin:0;font-size:13px;font-family:monospace;letter-spacing:2px;color:#FF4D6A;text-transform:uppercase;">🔔 New Order Alert</p>
          <p style="margin:6px 0 0;font-size:20px;font-weight:800;color:#E8EAF0;">Order <span style="color:#00FFD1">#{order_id}</span> received</p>
        </td></tr>

        <tr><td style="padding:32px 40px;">
          <!-- Customer -->
          <div style="background:#141B2D;border-radius:8px;padding:20px;margin-bottom:20px;">
            <p style="margin:0 0 12px;font-size:11px;color:#5A6380;font-family:monospace;letter-spacing:2px;text-transform:uppercase;">Customer</p>
            <p style="margin:0 0 4px;font-size:15px;font-weight:700;color:#E8EAF0;">{name}</p>
            <p style="margin:0 0 4px;font-size:13px;color:#5A6380;">{email}</p>
            <p style="margin:0;font-size:13px;color:#5A6380;">{address}</p>
          </div>

          <!-- Items -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
            <tr style="background:#141B2D;">
              <th style="padding:10px;text-align:left;font-size:10px;color:#5A6380;letter-spacing:1px;text-transform:uppercase;border-bottom:1px solid rgba(0,255,209,0.12);" colspan="2">Item</th>
              <th style="padding:10px;text-align:left;font-size:10px;color:#5A6380;letter-spacing:1px;text-transform:uppercase;border-bottom:1px solid rgba(0,255,209,0.12);">Qty</th>
              <th style="padding:10px;text-align:left;font-size:10px;color:#5A6380;letter-spacing:1px;text-transform:uppercase;border-bottom:1px solid rgba(0,255,209,0.12);">Subtotal</th>
            </tr>
            {rows}
          </table>

          <div style="padding:16px 20px;background:#141B2D;border-radius:6px;display:flex;justify-content:space-between;">
            <span style="color:#5A6380;font-size:13px;">Total Revenue</span>
            <span style="color:#00FFD1;font-size:22px;font-weight:800;font-family:monospace;">${total:,.0f}</span>
          </div>
        </td></tr>

        <tr><td style="padding:20px 40px;border-top:1px solid rgba(0,255,209,0.08);background:#080B12;">
          <p style="margin:0;font-size:12px;color:#5A6380;text-align:center;font-family:monospace;">NexusStore Admin · {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

# ── Schemas ────────────────────────────────────────────────────────────────────
class CartItemRequest(BaseModel):
    product_id: int
    quantity: int = 1

class CheckoutRequest(BaseModel):
    cart_id: str
    name: str
    email: str
    address: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

# ── Products ───────────────────────────────────────────────────────────────────
@app.get("/products")
def get_products(cat: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(ProductDB)
    if cat:
        q = q.filter(ProductDB.cat == cat)
    return q.all()

@app.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return p

# ── Cart ───────────────────────────────────────────────────────────────────────
@app.post("/cart")
def create_cart(db: Session = Depends(get_db)):
    cart_id = str(uuid.uuid4())
    db.add(CartDB(id=cart_id))
    db.commit()
    return {"cart_id": cart_id}

@app.get("/cart/{cart_id}")
def get_cart(cart_id: str, db: Session = Depends(get_db)):
    cart = db.query(CartDB).filter(CartDB.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    items, total = [], 0
    for item in cart.items:
        items.append({"product_id": item.product_id, "name": item.product.name, "icon": item.product.icon, "price": item.product.price, "quantity": item.quantity})
        total += item.product.price * item.quantity
    return {"cart_id": cart_id, "items": items, "total": total}

@app.post("/cart/{cart_id}/add")
def add_to_cart(cart_id: str, item: CartItemRequest, db: Session = Depends(get_db)):
    cart = db.query(CartDB).filter(CartDB.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    product = db.query(ProductDB).filter(ProductDB.id == item.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    existing = next((i for i in cart.items if i.product_id == item.product_id), None)
    if existing:
        existing.quantity += item.quantity
    else:
        db.add(CartItemDB(cart_id=cart_id, product_id=item.product_id, quantity=item.quantity))
    db.commit()
    return {"message": "Item added"}

@app.delete("/cart/{cart_id}/remove/{product_id}")
def remove_from_cart(cart_id: str, product_id: int, db: Session = Depends(get_db)):
    item = db.query(CartItemDB).filter(CartItemDB.cart_id == cart_id, CartItemDB.product_id == product_id).first()
    if item:
        db.delete(item)
        db.commit()
    return {"message": "Item removed"}

# ── Checkout ───────────────────────────────────────────────────────────────────
@app.post("/checkout")
async def checkout(req: CheckoutRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    cart = db.query(CartDB).filter(CartDB.id == req.cart_id).first()
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty or not found")

    total = sum(i.product.price * i.quantity for i in cart.items)
    order_id = str(uuid.uuid4())[:8].upper()

    order = OrderDB(id=order_id, name=req.name, email=req.email, address=req.address, total=total)
    db.add(order)

    items_snapshot = []
    for item in cart.items:
        items_snapshot.append({"icon": item.product.icon, "name": item.product.name, "price": item.product.price, "quantity": item.quantity})
        db.add(OrderItemDB(order_id=order_id, product_id=item.product_id, name=item.product.name, icon=item.product.icon, price=item.product.price, quantity=item.quantity))
        db.delete(item)

    db.commit()

    # Send emails in background (non-blocking)
    background_tasks.add_task(
        send_email,
        req.email,
        f"🎉 Order #{order_id} Confirmed — NexusStore",
        user_email_html(order_id, req.name, req.address, items_snapshot, total)
    )
    background_tasks.add_task(
        send_email,
        ADMIN_EMAIL,
        f"🔔 New Order #{order_id} — ${total:,.0f} from {req.name}",
        admin_email_html(order_id, req.name, req.email, req.address, items_snapshot, total)
    )

    return {"message": "Order placed!", "order_id": order_id, "total": total}

@app.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order_id": order.id, "name": order.name, "email": order.email, "address": order.address, "total": order.total, "status": order.status, "created_at": order.created_at, "items": [{"name": i.name, "icon": i.icon, "price": i.price, "quantity": i.quantity} for i in order.items]}

# ── Auth ───────────────────────────────────────────────────────────────────────
@app.post("/register")
async def register(req: RegisterRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = UserDB(name=req.name, email=req.email, password=req.password)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Welcome email
    background_tasks.add_task(
        send_email,
        req.email,
        "Welcome to NexusStore 🚀",
        f"""
<!DOCTYPE html><html><body style="margin:0;padding:0;background:#080B12;font-family:'Helvetica Neue',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#080B12;padding:40px 0;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#0E1420;border:1px solid rgba(0,255,209,0.12);border-radius:12px;overflow:hidden;">
<tr><td style="padding:36px 40px;border-bottom:1px solid rgba(0,255,209,0.12);">
  <p style="margin:0;font-size:22px;font-weight:800;color:#00FFD1;">NEXUS<span style="color:#E8EAF0">STORE</span></p>
</td></tr>
<tr><td style="padding:36px 40px;">
  <p style="font-size:28px;font-weight:800;color:#E8EAF0;margin:0 0 12px;">Welcome, {req.name.split()[0]}! 🚀</p>
  <p style="color:#5A6380;font-size:14px;line-height:1.8;margin:0 0 28px;">Your NexusStore account is ready. You now have access to exclusive drops, order tracking, and fast checkout.</p>
  <div style="background:#141B2D;border-radius:8px;padding:20px;margin-bottom:24px;">
    <p style="margin:0 0 6px;font-size:11px;color:#5A6380;font-family:monospace;letter-spacing:2px;text-transform:uppercase;">Your Account</p>
    <p style="margin:0;font-size:14px;color:#E8EAF0;">{req.name} · {req.email}</p>
  </div>
  <p style="color:#5A6380;font-size:13px;line-height:1.7;margin:0;">Start exploring our latest collection — new drops every week.</p>
</td></tr>
<tr><td style="padding:20px 40px;border-top:1px solid rgba(0,255,209,0.08);background:#080B12;">
  <p style="margin:0;font-size:12px;color:#5A6380;text-align:center;">© 2077 NexusStore · Built for the future</p>
</td></tr>
</table></td></tr></table>
</body></html>"""
    )

    return {"message": "Account created!", "user_id": user.id, "name": user.name, "email": user.email}

@app.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == req.email, UserDB.password == req.password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"message": "Logged in!", "user_id": user.id, "name": user.name, "email": user.email}

@app.get("/users/{user_id}/orders")
def get_user_orders(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return [{"order_id": o.id, "total": o.total, "status": o.status, "created_at": o.created_at, "items": [{"name": i.name, "icon": i.icon, "price": i.price, "quantity": i.quantity} for i in o.items]} for o in user.orders]