import React from 'react';
import { NavLink } from 'react-router-dom';

const links = [
  ['/farmer', 'Dashboard', true], ['/farmer/products', 'Products'], ['/farmer/orders', 'Orders'],
  ['/farmer/insights', 'AI Insights'], ['/farmer/profile', 'Farm profile'], ['/farmer/kyc', 'KYC'],
];
export default function FarmerNav() {
  return (
    <div className="subnav">
      {links.map(([to, label, end]) => <NavLink key={to} to={to} end={end}>{label}</NavLink>)}
    </div>
  );
}
