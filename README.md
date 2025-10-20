# Django-Advance-Practice

## 📚 Django REST Framework APIs - Complete Guide

### 🎯 Overview

Dự án Django với các API endpoints đầy đủ sử dụng **Django REST Framework** và **JWT Bearer Token Authentication**.

---

## 📦 Features Implemented

### ✅ Authentication System
- JWT Bearer Token authentication
- User registration với auto token generation
- Login/Logout với token management
- Token refresh mechanism
- Access token: 5 giờ | Refresh token: 1 ngày

### ✅ Category APIs
- Full CRUD operations
- Tree structure support (parent-child categories)
- Image upload for categories
- Search và filtering
- Get category tree/root/children
- Get products in category

### ✅ Product APIs
- Full CRUD operations
- Multiple image upload
- Thumbnail management
- Multiple categories per product
- Auto view count increment
- Search, filter, ordering
- Price range filtering
- Most viewed / Latest products
- Voucher system

### ✅ Product Comments
- CRUD operations
- User authentication required
- Owner-only edit/delete
- Filter by product/user

### ✅ Voucher System
- User voucher management
- One voucher per user per product
- Unique voucher codes

### ✅ Report APIs
- **Total products per category**
- **Total views of a product**
- **Total comments on a product**
- **Category statistics** (products, views, comments)

---

## 📊 API Summary

**Total Endpoints:** 39

| Category | Count | Description |
|----------|-------|-------------|
| Authentication | 4 | Register, Login, Logout, Refresh |
| Categories | 9 | CRUD + Tree/Root/Children/Products |
| Products | 10 | CRUD + Images/Thumbnail/Views/Latest |
| Product Images | 5 | Standard CRUD operations |
| Comments | 4 | CRUD with owner permissions |
| Vouchers | 2 | List/Detail (user's own) |
| Reports | 5 | Analytics reports |

---

## 🚀 Quick Start

### 1. Authentication

```bash
# Register user
curl -X POST http://127.0.0.1:8000/user/api/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "Test123!",
    "password2": "Test123!"
  }'

# Save the access token from response
export TOKEN="eyJhbGc..."
```

### 2. Use Bearer Token

Add header to every request:

```
Authorization: Bearer <access_token>
```

### 3. Example Requests

```bash
# Get all products
curl -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8000/catalog/api/products/

# Get products per category report
curl -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8000/catalog/api/reports/products-per-category/

# Get product views
curl -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8000/catalog/api/reports/product-views/1/
```

---

## 📖 Documentation

### API Documentation
- **[Complete API Documentation](./advance_practice/docs/API_COMPLETE_DOCUMENTATION.md)** - Chi tiết tất cả 39 endpoints
- **[Report APIs Quick Reference](./advance_practice/docs/REPORT_APIs_QUICK_REFERENCE.md)** - Quick reference cho Report APIs

### Django Admin
- **[Django Admin Guide](./advance_practice/DJANGO_ADMIN_GUIDE.md)**
- **[Admin Quick Start](./advance_practice/ADMIN_QUICKSTART.md)**

---

## 🔑 Key Endpoints

### Authentication
```
POST   /user/api/register/          - Register user
POST   /user/api/login/             - Login user
POST   /user/api/token/refresh/     - Refresh access token
POST   /user/api/logout/            - Logout user
```

### Reports (NEW!)
```
GET    /catalog/api/reports/                        - Available reports
GET    /catalog/api/reports/products-per-category/  - Products per category
GET    /catalog/api/reports/product-views/{id}/     - Product views
GET    /catalog/api/reports/product-comments/{id}/  - Product comments
GET    /catalog/api/reports/category-stats/         - Category statistics
```

### Products
```
GET    /catalog/api/products/                      - List products
POST   /catalog/api/products/                      - Create product
GET    /catalog/api/products/{id}/                 - Get product (auto +1 view)
POST   /catalog/api/products/{id}/upload_images/   - Upload images
GET    /catalog/api/products/most_viewed/          - Most viewed
GET    /catalog/api/products/latest/               - Latest products
```

See [Complete API Documentation](./advance_practice/docs/API_COMPLETE_DOCUMENTATION.md) for all endpoints.

---

## 💡 Example Code

### JavaScript (Axios)

```javascript
import axios from 'axios';

const api = axios.create({
    baseURL: 'http://127.0.0.1:8000',
    headers: {
        'Authorization': `Bearer ${accessToken}`
    }
});

// Get reports
const perCategory = await api.get('/catalog/api/reports/products-per-category/');
const productViews = await api.get('/catalog/api/reports/product-views/1/');
const categoryStats = await api.get('/catalog/api/reports/category-stats/');
```

### Python (Requests)

```python
import requests

headers = {'Authorization': f'Bearer {access_token}'}

# Get reports
response = requests.get(
    'http://127.0.0.1:8000/catalog/api/reports/products-per-category/',
    headers=headers
)
print(response.json())
```

---

## 🛡️ Permissions

| Endpoint Type | Public Read | Authenticated Write |
|---------------|-------------|---------------------|
| Authentication | ✅ | ✅ |
| Categories | ✅ | ✅ |
| Products | ✅ | ✅ |
| Comments | ✅ | ✅ (Owner only) |
| Vouchers | ❌ | ✅ (Own only) |
| Reports | ✅ | ✅ |

---

## ✅ All Features Complete!

- ✅ JWT Bearer Token Authentication
- ✅ Full CRUD operations
- ✅ Image upload support
- ✅ Search, filter, ordering
- ✅ Pagination
- ✅ **Report analytics**
- ✅ Tree structure categories
- ✅ Voucher system
- ✅ Auto view count

**Total: 39 API endpoints ready to use! 🚀**
