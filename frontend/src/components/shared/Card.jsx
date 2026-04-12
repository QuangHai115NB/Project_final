export default function Card({ children, className = '', onClick, hoverable = false }) {
  return (
    <div
      className={`
        bg-white rounded-2xl shadow-sm border border-gray-100 p-5
        ${hoverable ? 'cursor-pointer hover:shadow-md hover:border-primary/30 transition-all duration-200' : ''}
        ${onClick ? 'cursor-pointer hover:shadow-md transition-all' : ''}
        ${className}
      `}
      onClick={onClick}
    >
      {children}
    </div>
  );
}
