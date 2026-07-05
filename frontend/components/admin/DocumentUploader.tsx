"use client";

import { useState, useRef } from "react";
import { UploadCloud, FileType, CheckCircle, XCircle } from "lucide-react";
import { api } from "../../lib/api";

export function DocumentUploader({ onUploadComplete }: { onUploadComplete: () => void }) {
  const [isUploading, setIsUploading] = useState(false);
  const [status, setStatus] = useState<{ type: "success" | "error", message: string } | null>(null);
  const [category, setCategory] = useState("policies");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setStatus(null);

    try {
      await api.uploadDocument(file, category);
      setStatus({ type: "success", message: `Dokumen "${file.name}" berhasil diproses & di-index.` });
      onUploadComplete();
    } catch (error) {
      setStatus({ type: "error", message: error instanceof Error ? error.message : "Gagal mengupload dokumen." });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className="p-6 bg-white/5 border border-white/10 rounded-2xl">
      <h3 className="text-lg font-semibold text-white/90 mb-4">Upload Dokumen Baru</h3>
      
      <div className="flex flex-col md:flex-row gap-4 mb-4">
        <div className="flex-1">
          <label className="block text-sm text-white/60 mb-2">Kategori</label>
          <select 
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full p-2.5 bg-black/40 border border-white/10 rounded-xl text-white/90 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          >
            <option value="policies">Kebijakan Perusahaan (Policies)</option>
            <option value="technical">Dokumentasi Teknis (Technical)</option>
            <option value="onboarding">Materi Onboarding (Onboarding)</option>
            <option value="reports">Laporan (Reports)</option>
          </select>
        </div>
      </div>

      <div 
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
          isUploading ? "border-blue-500/50 bg-blue-500/5" : "border-white/20 hover:border-blue-400/50 bg-black/20 hover:bg-white/5"
        }`}
      >
        {isUploading ? (
          <div className="flex flex-col items-center justify-center space-y-4">
            <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
            <p className="text-blue-400 text-sm">Sedang mengekstrak teks, chunking, dan embedding...</p>
          </div>
        ) : (
          <label className="flex flex-col items-center justify-center cursor-pointer">
            <div className="p-3 bg-white/5 rounded-full mb-3 text-white/60">
              <UploadCloud className="w-8 h-8" />
            </div>
            <p className="text-sm font-medium text-white/80 mb-1">Klik untuk upload dokumen</p>
            <p className="text-xs text-white/40 mb-4">Mendukung PDF, DOCX, TXT (Max 5MB)</p>
            <div className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition-colors">
              Pilih File
            </div>
            <input 
              type="file" 
              className="hidden" 
              accept=".pdf,.docx,.txt"
              onChange={handleFileChange}
              ref={fileInputRef}
            />
          </label>
        )}
      </div>

      {status && (
        <div className={`mt-4 p-4 rounded-xl flex items-start space-x-3 text-sm ${
          status.type === "success" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"
        }`}>
          {status.type === "success" ? <CheckCircle className="w-5 h-5 flex-shrink-0" /> : <XCircle className="w-5 h-5 flex-shrink-0" />}
          <span>{status.message}</span>
        </div>
      )}
    </div>
  );
}
