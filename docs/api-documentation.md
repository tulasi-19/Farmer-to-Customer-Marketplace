# API reference — base URL `http://localhost:8000/api/v1`

Auth: `Authorization: Bearer <access>`. Errors are JSON: `{"detail": "..."}` or `{"field": ["..."]}`.
Codes: 200/201 ok · 204 no content · 400 validation · 401 not logged in · 403 wrong role · 404 not found *(also for other users' resources)* · 409 conflict · 422 model can't handle input · 429 rate-limited · 503 service unavailable (e.g. ML model not trained).
Lists are paginated: `{count, next, previous, results}` (`?page=`, `?page_size=` max 50).

## Auth
| Method & path | Who | Notes |
|---|---|---|
| POST `auth/register/` | public | role ∈ `farmer`,`customer` only (`admin` → 400) |
| POST `auth/login/` | public | → `{access, refresh}` |
| POST `auth/token/refresh/` | public | rotates refresh token |
| POST `auth/logout/` `{refresh}` | any | blacklists refresh |
| GET/PATCH `auth/me/` | any | role/username read-only |
| POST `auth/change-password/` · `forgot-password/` · `reset-password/` | | |

## Catalogue
GET `categories/` · GET `products/?search=&category=<slug>&min_price=&max_price=&available=true&farm=<id>&ordering=price|-price|-created_at|-avg_rating|name`
GET `products/<id>/` · GET `products/mine/` (farmer) · POST/PATCH/DELETE `products/…` (approved farmer, own products; delete archives if ordered)
GET `farms/`, `farms/<id>/` (approved farms only)

## Farmer
GET/POST/PATCH `farmer/profile/` · GET/POST `farmer/kyc/` (multipart: `id_type,id_number,document`) · GET `farmer/kyc/<id>/document/`
GET `farmer/dashboard/` · GET `farmer/shipments/?status=` · POST `farmer/shipments/<id>/status/`

## Customer
GET/DELETE `cart/` · POST `cart/items/` `{product_id, quantity}` · PATCH/DELETE `cart/items/<id>/`
POST `orders/checkout/` `{shipping_address, shipping_phone}` (cash on delivery) · GET `orders/`, `orders/<id>/` · POST `orders/<id>/cancel/`
GET/POST `reviews/` · GET `reviews/eligibility/?product=` · PATCH/DELETE `reviews/<id>/` (author)

## AI (farmer/admin)
POST `ai/demand-prediction/` · POST `ai/price-recommendation/` · GET `ai/model-info/` · GET `ai/history/`

## Admin
GET `admin/stats/` · GET `admin/users/`, PATCH `admin/users/<id>/ {is_active}` · GET `admin/kyc-applications/?status=`, POST `…/<id>/approve/`, `…/<id>/reject/ {reason}`, GET `…/<id>/document/`
GET `admin/products/`, PATCH `admin/products/<id>/ {is_active}` · GET `admin/orders/`, POST `admin/shipments/<id>/status/`, POST `admin/orders/<id>/mark-cod-paid/` · GET `admin/reviews/`, PATCH `admin/reviews/<id>/ {status}`

## Samples
**Checkout** `POST orders/checkout/`
```json
{"shipping_address":"12 MG Road, Visakhapatnam","shipping_phone":"9876543210"}
```
→ `201` `{"id":7,"status":"confirmed","payment_status":"cod_pending","total_amount":"160.00","can_cancel":true,"shipments":[{"farm_name":"Ravi Green Farm","status":"confirmed",...}],...}`
(prices/totals/status in the request would be ignored)

**Farmer updates tracking** `POST farmer/shipments/12/status/`
```json
{"status":"shipped","carrier":"BlueDart","tracking_number":"BD123","note":"Left the farm at 9am"}
```
→ `200` shipment with `"status":"shipped","allowed_next":["out_for_delivery","delivered"]`. Skipping a step → `400 {"status":"Cannot move a 'confirmed' shipment to 'delivered'."}`; another farmer's shipment → `404`; a customer → `403`.

**Demand prediction** `POST ai/demand-prediction/` `{"product_id":4}` →
```json
{"type":"demand","crop":"Tomato","region":"Andhra Pradesh","forecast_period":{"start":"2026-10-29","end":"2026-11-28","days":30},
 "predicted_units":986.3,"unit":"kg","range":{"low":820.1,"high":1120.4,"basis":"…"},
 "warnings":["No sales history for this product yet, …"],"reliability":"low",
 "model":{"data_source":"synthetic_demo","metrics":{"mae":…,"rmse":…,"r2":…}},"disclaimer":"…"}
```
(numbers illustrative) **Price** `POST ai/price-recommendation/` `{"product_id":4,"grade":"A","market_price_per_kg":30}` → `{"recommended_price":…,"currency":"INR","unit":"kg","applied_automatically":false,…}`
