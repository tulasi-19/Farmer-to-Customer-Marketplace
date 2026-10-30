import React from 'react';

export default function About() {
  return (
    <div className="container" style={{ maxWidth: 800 }}>
      <h1 className="section-title">About FarmBridge AI</h1>
      <p>FarmBridge AI connects verified farmers directly with customers. Farmers keep a fairer share of the price; customers get fresh produce and know exactly who grew it.</p>
      <h3>How it works</h3>
      <ol>
        <li><strong>Farmers</strong> register, submit identity (KYC) documents and, once an admin approves them, list produce.</li>
        <li><strong>Customers</strong> browse, order with cash on delivery, and track each farmer’s shipment.</li>
        <li><strong>AI insights</strong> give farmers a 30-day demand estimate and a suggested price. These come from models trained on <em>synthetic demonstration data</em>, so treat them as illustrations, not market advice.</li>
      </ol>
    </div>
  );
}
