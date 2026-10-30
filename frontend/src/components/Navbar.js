import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { cartAPI } from '../api/services';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [count, setCount] = useState(0);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (user?.role !== 'customer') { setCount(0); return undefined; }
    const load = () => cartAPI.get().then((c) => setCount(c.item_count)).catch(() => {});
    load();
    window.addEventListener('cart:changed', load);
    return () => window.removeEventListener('cart:changed', load);
  }, [user]);

  const go = () => setOpen(false);
  const doLogout = async () => { await logout(); setOpen(false); navigate('/'); };

  return (
    <header className="navbar">
      <Link to="/" className="brand" onClick={go}>🌾 FarmBridge AI</Link>
      <button className="menu-toggle" aria-label="Toggle menu" aria-expanded={open} onClick={() => setOpen(!open)}>☰</button>
      <nav className={open ? 'open' : ''}>
        <Link to="/products" onClick={go}>Products</Link>
        <Link to="/farms" onClick={go}>Farms</Link>
        <Link to="/about" onClick={go}>About</Link>
        <Link to="/contact" onClick={go}>Contact</Link>
        {user?.role === 'customer' && <>
          <Link to="/cart" onClick={go}>Cart {count > 0 && <span className="badge">{count}</span>}</Link>
          <Link to="/orders" onClick={go}>My Orders</Link>
          <Link to="/profile" onClick={go}>Profile</Link>
        </>}
        {user?.role === 'farmer' && <Link to="/farmer" onClick={go}>Farmer Dashboard</Link>}
        {user?.role === 'admin' && <Link to="/admin" onClick={go}>Admin</Link>}
        {user ? <button onClick={doLogout}>Logout ({user.username})</button> : <>
          <Link to="/login" onClick={go}>Login</Link>
          <Link to="/register" onClick={go}>Register</Link>
        </>}
      </nav>
    </header>
  );
}
