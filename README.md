# Private Shopping Platform (MVP)

This project delivers a minimal **私人购物平台** MVP built with **FastAPI + SQLAlchemy + SQLite**. The MVP focuses on direct ordering (no cart) and mock payments, while reserving integration points for Alipay/WeChat.

## Features

### 用户端
- 分类展示：`GET /categories`，点击分类查看商品列表 `GET /categories/{id}/products`
- 商品详情：`GET /products/{id}`
- 下单：直接下单 `POST /orders`（**无购物车**，请见下方说明）
- 支付（MVP Mock）：
  - 付款创建：`POST /payments/{order_id}/create`
  - Mock 支付通知：`POST /payments/mock/notify`

### 商户后台
- 商户登录（最简 token 方案，隔离商户数据）
- 商品管理：上架/修改/下架/改价/改库存/改分类
- 商户只能管理自己的商品/分类

### 支付扩展点
- Provider 结构已内置（mock/alipay/wechat）。
- 预留 `create` & `notify` 端点骨架，并带有通知幂等框架（同一 `out_trade_no` 重复通知不会重复改状态）。

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
uvicorn app.main:app --reload
```

默认数据库：`sqlite:///./shopping.db`

## 订单状态机

`CREATED -> PAYING -> PAID / FAILED / CANCELED`

- 创建订单：`CREATED`
- 创建支付单：`PAYING`
- 支付成功：`PAID`
- 支付失败：`FAILED`
- 订单取消：`CANCELED`

## 直接下单说明

MVP 采用**直接下单**模式（无购物车）：
1. 用户选择商品与数量调用 `POST /orders` 创建订单。
2. 再调用 `POST /payments/{order_id}/create` 创建支付单。

## CURL 验收示例（至少 6 条）

> 建议在终端里依次执行，替换 `TOKEN` / `ORDER_ID` / `OUT_TRADE_NO` / `PRODUCT_ID`。

1) 注册商户
```bash
curl -X POST http://127.0.0.1:8000/merchant/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo123"}'
```

2) 商户登录，获取 token
```bash
curl -X POST http://127.0.0.1:8000/merchant/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo123"}'
```

3) 创建分类
```bash
curl -X POST http://127.0.0.1:8000/merchant/categories \
  -H "Content-Type: application/json" \
  -H "X-Merchant-Token: TOKEN" \
  -d '{"name":"咖啡"}'
```

4) 创建商品
```bash
curl -X POST http://127.0.0.1:8000/merchant/products \
  -H "Content-Type: application/json" \
  -H "X-Merchant-Token: TOKEN" \
  -d '{"category_id":1,"name":"拿铁","price":25,"stock":20,"description":"热拿铁","image_url":"https://example.com/latte.jpg"}'
```

5) 用户查看分类 & 商品
```bash
curl http://127.0.0.1:8000/categories
curl http://127.0.0.1:8000/categories/1/products
```

6) 用户下单
```bash
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"product_id":1,"quantity":2}'
```

7) 创建支付单（mock）
```bash
curl -X POST http://127.0.0.1:8000/payments/ORDER_ID/create \
  -H "Content-Type: application/json" \
  -d '{"provider":"mock"}'
```

8) Mock 支付回调（SUCCESS）
```bash
curl -X POST http://127.0.0.1:8000/payments/mock/notify \
  -H "Content-Type: application/json" \
  -d '{"out_trade_no":"OUT_TRADE_NO","status":"SUCCESS"}'
```

9) Mock 支付回调（FAILED）
```bash
curl -X POST http://127.0.0.1:8000/payments/mock/notify \
  -H "Content-Type: application/json" \
  -d '{"out_trade_no":"OUT_TRADE_NO","status":"FAILED"}'
```

## Alipay / WeChat 接入说明

- 创建支付单仍走 `POST /payments/{order_id}/create`，传 `provider` 为 `alipay` / `wechat`。
- 通知端点分别为：
  - `POST /payments/alipay/notify`
  - `POST /payments/wechat/notify`

后续只需在 provider 中添加真实的签名校验与渠道 SDK 调用即可完成接入。
