import { useState, useRef } from 'react';
import { jdAPI } from '../../api/auth';
import { Button, Card } from '../shared';

export default function JDUploader({ onSuccess }) {
  const [mode, setMode] = useState('text'); // 'text' | 'file'
  const [jdText, setJdText] = useState('');
  const [title, setTitle] = useState('');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef();

  const handleUpload = async () => {
    if (mode === 'text' && !jdText.trim()) {
      setError('Vui lòng nhập nội dung JD');
      return;
    }
    if (mode === 'file' && !file) {
      setError('Vui lòng chọn file JD');
      return;
    }
    setUploading(true);
    setError('');
    try {
      const { data } = await jdAPI.upload(mode === 'text' ? jdText : null, title, mode === 'file' ? file : null);
      onSuccess?.(data);
    } catch (err) {
      setError(err.response?.data?.error || 'Upload thất bại');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card className="space-y-4">
      <h3 className="text-lg font-bold text-gray-800">💼 Upload JD</h3>

      {/* Mode toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => setMode('text')}
          className={`px-4 py-2 rounded-xl font-medium transition-all ${mode === 'text' ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600'}`}
        >
          📝 Nhập text
        </button>
        <button
          onClick={() => setMode('file')}
          className={`px-4 py-2 rounded-xl font-medium transition-all ${mode === 'file' ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600'}`}
        >
          📎 Upload file
        </button>
      </div>

      {mode === 'text' ? (
        <textarea
          placeholder="Dán nội dung Job Description vào đây..."
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          rows={8}
          className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none text-sm"
        />
      ) : (
        <div
          onClick={() => fileRef.current?.click()}
          className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-primary/50 hover:bg-gray-50 transition-all"
        >
          <input ref={fileRef} type="file" accept=".pdf,.txt" onChange={(e) => setFile(e.target.files[0])} className="hidden" />
          <div className="text-4xl mb-2">📎</div>
          {file ? (
            <p className="font-semibold text-primary">{file.name}</p>
          ) : (
            <p className="text-gray-500">Click để chọn file PDF hoặc TXT</p>
          )}
        </div>
      )}

      <input
        type="text"
        placeholder="Tiêu đề JD (tùy chọn)"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/50"
      />

      {error && <p className="text-red-500 text-sm">{error}</p>}

      <Button onClick={handleUpload} loading={uploading} className="w-full">
        {uploading ? 'Đang tải lên...' : 'Tải JD lên'}
      </Button>
    </Card>
  );
}