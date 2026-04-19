export default function Card({ children, className = '', onClick, hoverable = false }) {
  return (
    <div
      className={`
        rounded-lg border border-gray-100 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900
        ${hoverable ? 'cursor-pointer hover:shadow-md hover:border-primary/30 dark:hover:border-blue-400/50 transition-all duration-200' : ''}
        ${onClick ? 'cursor-pointer hover:shadow-md transition-all' : ''}
        ${className}
      `}
      onClick={onClick}
    >
      {children}
    </div>
  );
}
