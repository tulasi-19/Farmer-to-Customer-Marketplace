import api from './axiosClient';

const data = (p) => p.then((r) => r.data);

export const authAPI = {
  register: (b) => data(api.post('/auth/register/', b)),
  login: (b) => data(api.post('/auth/login/', b)),
  logout: (refresh) => api.post('/auth/logout/', { refresh }),
  me: () => data(api.get('/auth/me/')),
  updateMe: (b) => data(api.patch('/auth/me/', b)),
  changePassword: (b) => data(api.post('/auth/change-password/', b)),
  forgot: (b) => data(api.post('/auth/forgot-password/', b)),
  reset: (b) => data(api.post('/auth/reset-password/', b)),
};

export const productsAPI = {
  list: (params) => data(api.get('/products/', { params })),
  get: (id) => data(api.get(`/products/${id}/`)),
  mine: (params) => data(api.get('/products/mine/', { params })),
  create: (fd) => data(api.post('/products/', fd)),
  update: (id, body) => data(api.patch(`/products/${id}/`, body)),
  remove: (id) => data(api.delete(`/products/${id}/`)),
  categories: () => data(api.get('/categories/')),
};

export const farmsAPI = {
  list: (params) => data(api.get('/farms/', { params })),
  get: (id) => data(api.get(`/farms/${id}/`)),
  profile: () => data(api.get('/farmer/profile/')),
  saveProfile: (fd, exists) => data(exists ? api.patch('/farmer/profile/', fd) : api.post('/farmer/profile/', fd)),
  kyc: () => data(api.get('/farmer/kyc/')),
  submitKyc: (fd) => data(api.post('/farmer/kyc/', fd)),
  // Documents are private: fetched WITH the JWT and shown from an in-memory blob URL.
  document: (url) => api.get(url, { responseType: 'blob' }).then((r) => URL.createObjectURL(r.data)),
};

export const cartAPI = {
  get: () => data(api.get('/cart/')),
  add: (product_id, quantity) => data(api.post('/cart/items/', { product_id, quantity })),
  update: (id, quantity) => data(api.patch(`/cart/items/${id}/`, { quantity })),
  remove: (id) => data(api.delete(`/cart/items/${id}/`)),
  clear: () => data(api.delete('/cart/')),
};

export const ordersAPI = {
  checkout: (b) => data(api.post('/orders/checkout/', b)),
  list: (params) => data(api.get('/orders/', { params })),
  get: (id) => data(api.get(`/orders/${id}/`)),
  cancel: (id, reason) => data(api.post(`/orders/${id}/cancel/`, { reason })),
};

export const reviewsAPI = {
  list: (product, params) => data(api.get('/reviews/', { params: { product, ...params } })),
  create: (b) => data(api.post('/reviews/', b)),
  remove: (id) => api.delete(`/reviews/${id}/`),
  eligibility: (product) => data(api.get('/reviews/eligibility/', { params: { product } })),
};

export const farmerAPI = {
  dashboard: () => data(api.get('/farmer/dashboard/')),
  shipments: (params) => data(api.get('/farmer/shipments/', { params })),
  setStatus: (id, body) => data(api.post(`/farmer/shipments/${id}/status/`, body)),
};

export const aiAPI = {
  demand: (b) => data(api.post('/ai/demand-prediction/', b)),
  price: (b) => data(api.post('/ai/price-recommendation/', b)),
  info: () => data(api.get('/ai/model-info/')),
};

export const adminAPI = {
  stats: () => data(api.get('/admin/stats/')),
  users: (params) => data(api.get('/admin/users/', { params })),
  setUserActive: (id, is_active) => data(api.patch(`/admin/users/${id}/`, { is_active })),
  kyc: (params) => data(api.get('/admin/kyc-applications/', { params })),
  approveKyc: (id) => data(api.post(`/admin/kyc-applications/${id}/approve/`)),
  rejectKyc: (id, reason) => data(api.post(`/admin/kyc-applications/${id}/reject/`, { reason })),
  products: (params) => data(api.get('/admin/products/', { params })),
  setProductActive: (id, is_active) => data(api.patch(`/admin/products/${id}/`, { is_active })),
  orders: (params) => data(api.get('/admin/orders/', { params })),
  setShipmentStatus: (id, body) => data(api.post(`/admin/shipments/${id}/status/`, body)),
  markCodPaid: (id) => data(api.post(`/admin/orders/${id}/mark-cod-paid/`)),
  reviews: (params) => data(api.get('/admin/reviews/', { params })),
  moderateReview: (id, status) => data(api.patch(`/admin/reviews/${id}/`, { status })),
};
