export default function LoadingSpinner({ size = 'md', text = '' }) {
  const sizes = {
    sm: 'h-6 w-6 border-2',
    md: 'h-10 w-10 border-3',
    lg: 'h-16 w-16 border-4',
  };

  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div className={`${sizes[size]} animate-spin rounded-full border-primary border-t-transparent`}></div>
      {text && <p className="text-sm text-gray-500 dark:text-slate-400">{text}</p>}
    </div>
  );
}
