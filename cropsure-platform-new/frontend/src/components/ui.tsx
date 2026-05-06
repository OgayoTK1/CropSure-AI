import { PropsWithChildren } from 'react';

export function Card({ children }: PropsWithChildren) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      {children}
    </div>
  );
}

export function CardTitle({ children }: PropsWithChildren) {
  return <h2 className="text-base font-semibold text-slate-900">{children}</h2>;
}

export function Muted({ children }: PropsWithChildren) {
  return <p className="text-sm text-slate-600">{children}</p>;
}

export function Button(
  props: React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: 'primary' | 'secondary' | 'danger';
  }
) {
  const { variant = 'primary', className, ...rest } = props;
  const base =
    'inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed';
  const styles =
    variant === 'primary'
      ? 'bg-primary text-white hover:bg-primary-dark'
      : variant === 'danger'
        ? 'bg-red-600 text-white hover:bg-red-700'
        : 'bg-slate-100 text-slate-900 hover:bg-slate-200';
  return <button className={[base, styles, className].filter(Boolean).join(' ')} {...rest} />;
}

export function Badge({ children, tone = 'neutral' }: PropsWithChildren<{ tone?: 'neutral' | 'good' | 'warn' | 'bad' }>) {
  const cls =
    tone === 'good'
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : tone === 'warn'
        ? 'bg-amber-50 text-amber-700 border-amber-200'
        : tone === 'bad'
          ? 'bg-red-50 text-red-700 border-red-200'
          : 'bg-slate-50 text-slate-700 border-slate-200';
  return (
    <span className={[
      'inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium',
      cls,
    ].join(' ')}>
      {children}
    </span>
  );
}
