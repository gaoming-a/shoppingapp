from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .models import OrderStatus, PaymentStatus, ProductStatus


class MerchantCreate(BaseModel):
    username: str
    password: str


class MerchantLogin(BaseModel):
    username: str
    password: str


class MerchantOut(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    name: str


class CategoryOut(BaseModel):
    id: int
    name: str
    merchant_id: int

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    category_id: int
    name: str
    price: int
    stock: int
    description: str
    image_url: str
    status: ProductStatus = ProductStatus.ACTIVE


class ProductUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    price: Optional[int] = None
    stock: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[ProductStatus] = None


class ProductOut(BaseModel):
    id: int
    merchant_id: int
    category_id: int
    name: str
    price: int
    stock: int
    description: str
    image_url: str
    status: ProductStatus

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderOut(BaseModel):
    id: int
    product_id: int
    merchant_id: int
    quantity: int
    total_price: int
    status: OrderStatus
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    provider: str = Field(description="mock | alipay | wechat")


class PaymentOut(BaseModel):
    id: int
    order_id: int
    provider: str
    out_trade_no: str
    status: PaymentStatus
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentNotify(BaseModel):
    out_trade_no: str
    status: PaymentStatus


class HealthOut(BaseModel):
    status: str
