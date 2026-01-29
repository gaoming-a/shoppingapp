import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .models import Order, OrderStatus, Payment, PaymentStatus


class PaymentProvider:
    name: str

    def create(self, db: Session, order: Order) -> Payment:
        out_trade_no = uuid.uuid4().hex
        payment = Payment(
            order_id=order.id,
            provider=self.name,
            out_trade_no=out_trade_no,
            status=PaymentStatus.CREATED,
        )
        db.add(payment)
        return payment

    def notify(
        self, db: Session, out_trade_no: str, status_value: PaymentStatus
    ) -> tuple[Payment, bool]:
        payment = (
            db.query(Payment)
            .filter(Payment.out_trade_no == out_trade_no, Payment.provider == self.name)
            .one_or_none()
        )
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        if payment.status in {PaymentStatus.SUCCESS, PaymentStatus.FAILED}:
            return payment, False
        payment.status = status_value
        order = payment.order
        if order.status == OrderStatus.PAYING:
            if status_value == PaymentStatus.SUCCESS:
                order.status = OrderStatus.PAID
            elif status_value == PaymentStatus.FAILED:
                order.status = OrderStatus.FAILED
        return payment, True


class MockProvider(PaymentProvider):
    name = "mock"


class AlipayProvider(PaymentProvider):
    name = "alipay"


class WechatProvider(PaymentProvider):
    name = "wechat"


PROVIDERS: dict[str, PaymentProvider] = {
    "mock": MockProvider(),
    "alipay": AlipayProvider(),
    "wechat": WechatProvider(),
}


def get_provider(name: str) -> PaymentProvider:
    provider = PROVIDERS.get(name)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider"
        )
    return provider
