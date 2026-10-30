import React, { useState } from 'react';
import { useToast } from '../context/ToastContext';

export default function Contact() {
  const toast = useToast();
  const [sent, setSent] = useState(false);
  const submit = (e) => {
    e.preventDefault();
    // Demo only: there is no mail backend wired to this form yet (see README > Known limitations).
    setSent(true); toast('Thanks! (Demo form - message not actually sent.)');
  };
  return (
    <form className="form-card" onSubmit={submit}>
      <h2>Contact us</h2>
      <div className="form-group"><label htmlFor="cn">Name</label><input id="cn" required /></div>
      <div className="form-group"><label htmlFor="ce">Email</label><input id="ce" type="email" required /></div>
      <div className="form-group"><label htmlFor="cm">Message</label><textarea id="cm" rows={4} required /></div>
      {sent && <div className="alert alert-warn">Demo only: this form does not send email yet.</div>}
      <button className="btn btn-secondary" style={{ width: '100%' }}>Send</button>
    </form>
  );
}
