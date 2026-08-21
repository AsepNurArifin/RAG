"use client";

import { useState, useEffect } from "react";
import { FileText, Trash2, Calendar } from "lucide-react";
import { api } from "../../lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

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
    
    // Auto-refresh dimatikan sesuai permintaan
    // const interval = setInterval(() => {
    //   loadDocs();
    // }, 5000);
    
    // return () => clearInterval(interval);
  }, [refreshTrigger]);

  const handleDelete = async (id: string, filename: string) => {
    if (!confirm(`Hapus dokumen ${filename}?`)) return;
    try {
      await api.deleteDocument(id);
      loadDocs();
    } catch (e) {
      alert("Gagal menghapus dokumen");
    }
  };

  if (isLoading) {
    return (
      <div className="p-8 text-center text-slate-400 animate-pulse">
        Memuat metadata dokumen...
      </div>
    );
  }

  return (
    <>
      {/* Mobile Cards */}
      <div className="md:hidden space-y-3">
        {documents.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            Belum ada dokumen di database.
          </div>
        ) : (
          documents.map((doc) => (
            <div key={doc.id} className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <FileText className="w-5 h-5 text-[#0077ff] shrink-0" />
                  <div className="min-w-0">
                    <p className="font-medium text-slate-900 text-sm truncate" title={doc.filename}>{doc.filename}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="secondary" className="capitalize bg-slate-200/60 text-slate-700 hover:bg-slate-200 text-xs">
                        {doc.category}
                      </Badge>
                      <span className="text-xs text-slate-500">{doc.chunk_count} chunks</span>
                    </div>
                  </div>
                </div>
                <Button 
                  variant="ghost" 
                  size="icon"
                  onClick={() => handleDelete(doc.id, doc.filename)}
                  className="text-slate-400 hover:text-red-600 hover:bg-red-50 h-8 w-8 bg-transparent shrink-0"
                  title="Hapus Dokumen"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Desktop Table */}
      <div className="hidden md:block border border-slate-200 rounded-lg overflow-hidden bg-white">
        <div className="overflow-x-auto">
          <Table className="w-full">
            <TableHeader className="bg-[#0077ff]/5">
              <TableRow className="bg-transparent hover:bg-transparent border-b border-slate-200">
                <TableHead className="font-semibold text-slate-700 w-[40%]">Nama File</TableHead>
                <TableHead className="font-semibold text-slate-700 w-[20%]">Kategori</TableHead>
                <TableHead className="font-semibold text-slate-700 w-[10%]">Chunks</TableHead>
                <TableHead className="font-semibold text-slate-700 w-[20%]">Tanggal Upload</TableHead>
                <TableHead className="font-semibold text-slate-700 text-right w-[10%]">Aksi</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {documents.length === 0 ? (
                <TableRow className="bg-transparent hover:bg-transparent">
                  <TableCell colSpan={5} className="text-center py-8 text-slate-400">
                    Belum ada dokumen di database.
                  </TableCell>
                </TableRow>
              ) : (
                documents.map((doc) => (
                  <TableRow key={doc.id} className="bg-transparent hover:bg-[#0077ff]/5 border-b border-slate-200/60 transition-colors">
                    <TableCell className="font-medium text-slate-900 px-4">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-[#0077ff] shrink-0" />
                        <span className="truncate" title={doc.filename}>
                          {doc.filename}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="px-4">
                      <Badge variant="secondary" className="capitalize bg-slate-200/60 text-slate-700 hover:bg-slate-200">
                        {doc.category}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-slate-600 px-4">{doc.chunk_count}</TableCell>
                    <TableCell className="text-slate-600 px-4">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span>{new Date(doc.created_at).toLocaleDateString("id-ID")}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right px-4">
                      <Button 
                        variant="ghost" 
                        size="icon"
                        onClick={() => handleDelete(doc.id, doc.filename)}
                        className="text-slate-400 hover:text-red-600 hover:bg-red-50 h-8 w-8 bg-transparent"
                        title="Hapus Dokumen"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </>
  );
}
