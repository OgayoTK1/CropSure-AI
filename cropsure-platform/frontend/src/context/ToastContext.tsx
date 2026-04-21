import React, { createContext, useContext, useState, useCallback } from 'react';

interface ToastState {
  message: string;
  type: 'success' | 'error' | 'info';
  visible: boolean;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastState['type']) => void;
}

const ToastContext = createContext<ToastContextValue>({ showToast: () => {} });

export const useToast = () => useContext(ToastContext);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toast, setToast] = useState<ToastState>({ message: '', type: 'success', visible: false });

  const showToast = useCallback((message: string, type: ToastState['type'] = 'success') => {
    setToast({ message, type, visible: true });
    setTimeout(() => setToast((t) => ({ ...t, visible: false })), 5000);
  }, []);

  const bgColor = {
    success: 'bg-primary',
    error: 'bg-red-600',
    info: 'bg-blue-600',
  }[toast.type];

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {toast.visible && (
        <div
          className={`fixed bottom-6 right-4 left-4 md:left-auto md:w-96 z-[9999] ${bgColor} text-white px-5 py-4 rounded-xl shadow-2xl flex items-start gap-3 animate-fade-in`}
        >
          <svg className="w-5 h-5 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm font-medium leading-snug">{toast.message}</p>
          <button
            onClick={() => setToast((t) => ({ ...t, visible: false }))}
            className="ml-auto shrink-0 opacity-70 hover:opacity-100"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}
    </ToastContext.Provider>
  );
};