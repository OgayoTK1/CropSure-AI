import React from 'react';

interface Props {
  title: string;
  description?: string;
}

const EmptyState: React.FC<Props> = ({ title, description }) => (
  <div className="flex flex-col items-center justify-center gap-4 py-12 px-4 text-center">
    {/* Empty field SVG illustration */}
    <svg className="w-24 h-24" viewBox="0 0 96 96" fill="none">
      <rect x="8" y="60" width="80" height="4" rx="2" fill="#E5E7EB" />
      <rect x="16" y="50" width="64" height="12" rx="2" fill="#F3F4F6" />
      <path d="M48 50 C48 50 36 40 30 28 C38 30 44 38 48 44 C52 38 58 30 66 28 C60 40 48 50 48 50Z"
        fill="#D1FAE5" stroke="#6EE7B7" strokeWidth="1.5" />
      <path d="M48 44 L48 60" stroke="#6EE7B7" strokeWidth="2" strokeLinecap="round" />
      <circle cx="72" cy="30" r="8" fill="#FEF9C3" stroke="#FDE047" strokeWidth="1.5" />
      <path d="M72 20v-4M72 42v-4M62 30h-4M86 30h-4M65.2 23.2l-2.8-2.8M81.6 36.6l-2.8-2.8M65.2 36.8l-2.8 2.8M81.6 23.2l-2.8 2.8"
        stroke="#FDE047" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M20 50 C20 50 16 44 16 38 C20 40 22 46 22 46" fill="#D1FAE5" stroke="#6EE7B7" strokeWidth="1.5" />
      <path d="M22 46 L22 60" stroke="#6EE7B7" strokeWidth="2" strokeLinecap="round" />
    </svg>

    <div>
      <p className="font-semibold text-gray-700 text-base">{title}</p>
      {description && <p className="text-sm text-gray-400 mt-1 max-w-xs">{description}</p>}
    </div>
  </div>
);

export default EmptyState;