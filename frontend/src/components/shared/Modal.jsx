import { useEffect } from 'react';

export default function Modal({ isOpen, onClose, title, children, size = 'md' }) {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  if (!isOpen) return null;

  const sizes = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-6xl',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className={`relative max-h-[90vh] w-full overflow-y-auto rounded-lg bg-white shadow-2xl dark:bg-slate-900 ${sizes[size]}`}>
        <div className="sticky top-0 flex items-center justify-between rounded-t-lg border-b border-gray-100 bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-xl font-bold text-gray-800 dark:text-slate-100">{title}</h2>
          <button onClick={onClose} className="text-2xl leading-none text-gray-400 hover:text-gray-600 dark:hover:text-slate-200">×</button>
        </div>
        <div className="p-6 text-gray-800 dark:text-slate-100">{children}</div>
      </div>
    </div>
  );
}
