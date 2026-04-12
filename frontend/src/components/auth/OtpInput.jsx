import { useState, useRef, useEffect } from 'react';

export default function OtpInput({ value, onChange, length = 6 }) {
  const [digits, setDigits] = useState(Array(length).fill(''));
  const inputsRef = useRef([]);

  useEffect(() => {
    const filled = digits.join('');
    onChange(filled);
  }, [digits]);

  const handleChange = (index, val) => {
    if (!/^\d?$/.test(val)) return;
    const newDigits = [...digits];
    newDigits[index] = val;
    setDigits(newDigits);
    if (val && index < length - 1) {
      inputsRef.current[index + 1]?.focus();
    }
    if (filled === length) return;
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
    if (e.key === 'ArrowLeft' && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
    if (e.key === 'ArrowRight' && index < length - 1) {
      inputsRef.current[index + 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, length);
    if (!pasted) return;
    const newDigits = [...digits];
    pasted.split('').forEach((char, i) => { if (i < length) newDigits[i] = char; });
    setDigits(newDigits);
    inputsRef.current[Math.min(pasted.length, length - 1)]?.focus();
  };

  return (
    <div className="flex gap-2 justify-center" onPaste={handlePaste}>
      {digits.map((digit, i) => (
        <input
          key={i}
          ref={(el) => (inputsRef.current[i] = el)}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={digit}
          onChange={(e) => handleChange(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(i, e)}
          className="w-12 h-14 text-center text-2xl font-bold border-2 border-gray-300 rounded-xl
                     focus:border-primary focus:ring-2 focus:ring-primary/30 focus:outline-none
                     transition-all"
        />
      ))}
    </div>
  );
}