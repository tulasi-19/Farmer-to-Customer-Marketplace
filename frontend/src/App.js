import React from 'react';
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';

import Home from './pages/Home';
import Products from './pages/Products';
import ProductDetail from './pages/ProductDetail';
import { FarmList, FarmProfile } from './pages/Farms';
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import About from './pages/About';
import Contact from './pages/Contact';
import Cart from './pages/Cart';
import Checkout from './pages/Checkout';
import Orders from './pages/Orders';
import OrderDetail from './pages/OrderDetail';
import Profile from './pages/Profile';
import FarmerDashboard from './pages/FarmerDashboard';
import FarmerProfile from './pages/FarmerProfile';
import FarmerKYC from './pages/FarmerKYC';
import FarmerProducts from './pages/FarmerProducts';
import FarmerOrders from './pages/FarmerOrders';
import FarmerInsights from './pages/FarmerInsights';
import AdminDashboard from './pages/AdminDashboard';

const customer = (el) => <ProtectedRoute allowedRoles={['customer']}>{el}</ProtectedRoute>;
const farmer = (el) => <ProtectedRoute allowedRoles={['farmer']}>{el}</ProtectedRoute>;
const admin = (el) => <ProtectedRoute allowedRoles={['admin']}>{el}</ProtectedRoute>;

const NotFound = () => <div className="container center-note"><h2>Page not found</h2><Link to="/">Go home</Link></div>;

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Navbar />
          <main>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/products" element={<Products />} />
              <Route path="/products/:id" element={<ProductDetail />} />
              <Route path="/farms" element={<FarmList />} />
              <Route path="/farms/:id" element={<FarmProfile />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/about" element={<About />} />
              <Route path="/contact" element={<Contact />} />

              <Route path="/cart" element={customer(<Cart />)} />
              <Route path="/checkout" element={customer(<Checkout />)} />
              <Route path="/orders" element={customer(<Orders />)} />
              <Route path="/orders/:id" element={customer(<OrderDetail />)} />
              <Route path="/profile" element={customer(<Profile />)} />

              <Route path="/farmer" element={farmer(<FarmerDashboard />)} />
              <Route path="/farmer/profile" element={farmer(<FarmerProfile />)} />
              <Route path="/farmer/kyc" element={farmer(<FarmerKYC />)} />
              <Route path="/farmer/products" element={farmer(<FarmerProducts />)} />
              <Route path="/farmer/orders" element={farmer(<FarmerOrders />)} />
              <Route path="/farmer/insights" element={farmer(<FarmerInsights />)} />

              <Route path="/admin" element={admin(<AdminDashboard />)} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
          <div className="footer">🌾 FarmBridge AI — Connecting Farmers, Predicting Demand, Delivering Freshness</div>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}
