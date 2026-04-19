import { useCallback, useEffect, useState } from 'react';

export function Toast({ message, type = 'info', onClose, duration = 5000 }) {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(onClose, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  const colors = {
    success: 'bg-success text-white',
    error: 'bg-danger text-white',
    warning: 'bg-warning text-white',
    info: 'bg-primary text-white',
  };

  const icons = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ',
  };

  return (
    <div className={`fixed top-4 right-4 z-50 flex max-w-md items-center gap-3 rounded-lg px-5 py-3 shadow-lg ${colors[type]} animate-slide-in`}>
      <span className="font-bold text-lg">{icons[type]}</span>
      <span className="font-medium">{message}</span>
      <button onClick={onClose} className="ml-2 opacity-70 hover:opacity-100 text-xl leading-none">×</button>
    </div>
  );
}

export function useToast() {
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'info', duration = 5000) => {
    setToast({ message, type, duration });
  };
  const hideToast = useCallback(() => setToast(null), []);

  return { toast, showToast, hideToast };
}
