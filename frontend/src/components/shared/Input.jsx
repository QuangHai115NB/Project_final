export default function Input({
  label,
  error,
  className = '',
  ...props
}) {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      {label && <label className="text-sm font-medium text-gray-700">{label}</label>}
      <input
        className={`
          px-4 py-2.5 rounded-xl border text-base
          focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all
          ${error ? 'border-danger ring-2 ring-red-100' : 'border-gray-300 hover:border-gray-400'}
        `}
        {...props}
      />
      {error && <p className="text-sm text-danger">{error}</p>}
    </div>
  );
}
