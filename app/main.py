from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from . import auth
from .database import Base, engine
from .models import (
    Category,
    Merchant,
    Order,
    OrderStatus,
    PaymentStatus,
    Product,
    ProductStatus,
)
from .payment import get_provider
from .schemas import (
    CategoryCreate,
    CategoryOut,
    HealthOut,
    MerchantCreate,
    MerchantLogin,
    MerchantOut,
    OrderCreate,
    OrderOut,
    PaymentCreate,
    PaymentNotify,
    PaymentOut,
    ProductCreate,
    ProductOut,
    ProductUpdate,
)

app = FastAPI(title="Private Shopping Platform")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(status="ok")


@app.post("/merchant/register", response_model=MerchantOut)
def register_merchant(payload: MerchantCreate, db: Session = Depends(auth.get_db)):
    existing = db.query(Merchant).filter(Merchant.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    merchant = Merchant(
        username=payload.username,
        password_hash=auth.hash_password(payload.password),
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return merchant


@app.post("/merchant/login")
def merchant_login(payload: MerchantLogin, db: Session = Depends(auth.get_db)):
    merchant = db.query(Merchant).filter(Merchant.username == payload.username).first()
    if not merchant or merchant.password_hash != auth.hash_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    merchant.token = auth.create_token()
    db.commit()
    return {"token": merchant.token}


@app.post("/merchant/categories", response_model=CategoryOut)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(auth.get_db),
    merchant: Merchant = Depends(auth.get_current_merchant),
):
    category = Category(name=payload.name, merchant_id=merchant.id)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@app.get("/merchant/categories", response_model=list[CategoryOut])
def list_merchant_categories(
    db: Session = Depends(auth.get_db),
    merchant: Merchant = Depends(auth.get_current_merchant),
):
    return db.query(Category).filter(Category.merchant_id == merchant.id).all()


@app.post("/merchant/products", response_model=ProductOut)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(auth.get_db),
    merchant: Merchant = Depends(auth.get_current_merchant),
):
    category = (
        db.query(Category)
        .filter(Category.id == payload.category_id, Category.merchant_id == merchant.id)
        .one_or_none()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    product = Product(
        merchant_id=merchant.id,
        category_id=payload.category_id,
        name=payload.name,
        price=payload.price,
        stock=payload.stock,
        description=payload.description,
        image_url=payload.image_url,
        status=payload.status,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.patch("/merchant/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(auth.get_db),
    merchant: Merchant = Depends(auth.get_current_merchant),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.merchant_id == merchant.id)
        .one_or_none()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "category_id" and value is not None:
            category = (
                db.query(Category)
                .filter(Category.id == value, Category.merchant_id == merchant.id)
                .one_or_none()
            )
            if not category:
                raise HTTPException(status_code=404, detail="Category not found")
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@app.get("/merchant/products", response_model=list[ProductOut])
def list_merchant_products(
    db: Session = Depends(auth.get_db),
    merchant: Merchant = Depends(auth.get_current_merchant),
):
    return db.query(Product).filter(Product.merchant_id == merchant.id).all()


@app.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(auth.get_db)):
    return db.query(Category).all()


@app.get("/categories/{category_id}/products", response_model=list[ProductOut])
def list_category_products(category_id: int, db: Session = Depends(auth.get_db)):
    return (
        db.query(Product)
        .filter(
            Product.category_id == category_id,
            Product.status == ProductStatus.ACTIVE,
        )
        .all()
    )


@app.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(auth.get_db)):
    product = db.query(Product).filter(Product.id == product_id).one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def _adjust_stock(product: Product, delta: int) -> None:
    product.stock += delta
    if product.stock < 0:
        raise HTTPException(status_code=400, detail="Insufficient stock")


@app.post("/orders", response_model=OrderOut)
def create_order(payload: OrderCreate, db: Session = Depends(auth.get_db)):
    product = db.query(Product).filter(Product.id == payload.product_id).one_or_none()
    if not product or product.status != ProductStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Product not found")
    _adjust_stock(product, -payload.quantity)
    order = Order(
        product_id=product.id,
        merchant_id=product.merchant_id,
        quantity=payload.quantity,
        total_price=product.price * payload.quantity,
        status=OrderStatus.CREATED,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(auth.get_db)):
    order = db.query(Order).filter(Order.id == order_id).one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.post("/orders/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, db: Session = Depends(auth.get_db)):
    order = db.query(Order).filter(Order.id == order_id).one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in {OrderStatus.CREATED, OrderStatus.PAYING}:
        raise HTTPException(status_code=400, detail="Order cannot be canceled")
    order.status = OrderStatus.CANCELED
    _adjust_stock(order.product, order.quantity)
    db.commit()
    db.refresh(order)
    return order


@app.post("/payments/{order_id}/create", response_model=PaymentOut)
def create_payment(
    order_id: int, payload: PaymentCreate, db: Session = Depends(auth.get_db)
):
    order = db.query(Order).filter(Order.id == order_id).one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.CREATED:
        raise HTTPException(status_code=400, detail="Order not in CREATED state")
    provider = get_provider(payload.provider)
    order.status = OrderStatus.PAYING
    payment = provider.create(db, order)
    db.commit()
    db.refresh(payment)
    return payment


@app.post("/payments/mock/notify", response_model=PaymentOut)
def mock_notify(payload: PaymentNotify, db: Session = Depends(auth.get_db)):
    provider = get_provider("mock")
    payment, changed = provider.notify(db, payload.out_trade_no, payload.status)
    if changed and payload.status == PaymentStatus.FAILED:
        _adjust_stock(payment.order.product, payment.order.quantity)
    db.commit()
    db.refresh(payment)
    return payment


@app.post("/payments/alipay/notify", response_model=PaymentOut)
def alipay_notify(payload: PaymentNotify, db: Session = Depends(auth.get_db)):
    provider = get_provider("alipay")
    payment, changed = provider.notify(db, payload.out_trade_no, payload.status)
    if changed and payload.status == PaymentStatus.FAILED:
        _adjust_stock(payment.order.product, payment.order.quantity)
    db.commit()
    db.refresh(payment)
    return payment


@app.post("/payments/wechat/notify", response_model=PaymentOut)
def wechat_notify(payload: PaymentNotify, db: Session = Depends(auth.get_db)):
    provider = get_provider("wechat")
    payment, changed = provider.notify(db, payload.out_trade_no, payload.status)
    if changed and payload.status == PaymentStatus.FAILED:
        _adjust_stock(payment.order.product, payment.order.quantity)
    db.commit()
    db.refresh(payment)
    return payment
