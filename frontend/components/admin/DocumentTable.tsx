"use client";

import { useState, useEffect } from "react";
import { FileText, Trash2, Calendar } from "lucide-react";
import { api } from "../../lib/api";

export function DocumentTable({ refreshTrigger }: { refreshTrigger: number }) {
  const [documents, setDocuments] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadDocs = async () => {
    setIsLoading(true);
    try {
      const data = await api.getDocuments();
      setDocuments(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocs();
  }, [refreshTrigger]);

  const handleDelete = async (id: string, filename: string) => {
    if (!confirm(`Hapus dokumen ${filename}?`)) return;
    try {
      await api.deleteDocument(id, filename);
      loadDocs();
    } catch (e) {
      alert("Gagal menghapus dokumen");
    }
  };

  if (isLoading) {
    return <div className="p-8 text-center text-white/50 animate-pulse">Memuat metadata dokumen...</div>;
  }

  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
      <div className="p-4 border-b border-white/10 bg-black/20">
        <h3 className="font-semibold text-white/90">Knowledge Base ({documents.length})</h3>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-white/50 uppercase bg-black/40 border-b border-white/10">
            <tr>
              <th className="px-6 py-3 font-medium">Nama File</th>
              <th className="px-6 py-3 font-medium">Kategori</th>
              <th className="px-6 py-3 font-medium">Chunks</th>
              <th className="px-6 py-3 font-medium">Tanggal Upload</th>
              <th className="px-6 py-3 font-medium text-right">Aksi</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {documents.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-white/40">
                  Belum ada dokumen di database.
                </td>
              </tr>
            ) : (
              documents.map((doc) => (
                <tr key={doc.id} className="hover:bg-white/5 transition-colors">
                  <td className="px-6 py-4 font-medium text-white/80 flex items-center">
                    <FileText className="w-4 h-4 mr-2 text-blue-400" />
                    {doc.filename}
                  </td>
                  <td className="px-6 py-4">
                    <span className="px-2 py-1 rounded bg-white/10 text-xs text-white/70 capitalize">
                      {doc.category}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-white/60">{doc.chunk_count}</td>
                  <td className="px-6 py-4 text-white/60">
                    <div className="flex items-center">
                      <Calendar className="w-3 h-3 mr-1.5" />
                      {new Date(doc.upload_date).toLocaleDateString("id-ID")}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button 
                      onClick={() => handleDelete(doc.id, doc.filename)}
                      className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                      title="Hapus Dokumen"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
