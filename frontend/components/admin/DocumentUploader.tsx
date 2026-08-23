"use client";

import { useState, useRef, useEffect } from "react";
import { UploadCloud, CheckCircle, XCircle } from "lucide-react";
import { api } from "../../lib/api";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

const TERMINAL_STATUSES = new Set(["COMPLETED", "FAILED", "CANCELED", "TERMINATED", "TIMED_OUT"]);

export function DocumentUploader({ onUploadComplete }: { onUploadComplete: () => void }) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadPhase, setUploadPhase] = useState<"upload" | "processing" | "polling">("upload");
  const [status, setStatus] = useState<{ type: "success" | "error", message: string } | null>(null);
  const [category, setCategory] = useState("policies");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadPhase("upload");
    setStatus(null);

    try {
      setUploadPhase("upload");
      const upload = await api.uploadDocument(file, category);
      setUploadPhase("polling");

      // Poll status workflow hingga terminal (indexed/failed) dengan backoff.
      const delays = [1500, 2500, 4000, 6000, 8000, 10000];
      let workflowStatus: string | null = null;
      let workflowError: string | null = null;
      let workflowDomain: string | null = null;

      for (const delay of delays) {
        await new Promise((r) => setTimeout(r, delay));
        try {
          const wf = await api.getWorkflowStatus(upload.workflow_id);
          workflowStatus = wf.status;
          workflowDomain = wf.workflow_status || null;
          workflowError = wf.error || null;
          if (TERMINAL_STATUSES.has(wf.status)) break;
        } catch {
          // Workflow mungkin belum terdaftar; lanjut polling.
        }
      }

      const isIndexed = workflowStatus === "COMPLETED" && workflowDomain !== "failed";
      if (isIndexed) {
        setStatus({ type: "success", message: `Dokumen "${file.name}" berhasil di-index.` });
      } else if (workflowStatus === "FAILED" || workflowDomain === "failed") {
        setStatus({ type: "error", message: `Dokumen "${file.name}" gagal diproses: ${workflowError || "unknown error"}` });
      } else {
        setStatus({ type: "success", message: `Dokumen "${file.name}" dijadwalkan (${workflowStatus || "queued"}). Cek tabel dokumen untuk status akhir.` });
      }
      onUploadComplete();
    } catch (error) {
      setStatus({ type: "error", message: error instanceof Error ? error.message : "Gagal mengupload dokumen." });
    } finally {
      setIsUploading(false);
      setUploadPhase("upload");
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <Label htmlFor="category-select" className="text-slate-600 mb-2 block font-medium text-sm">Kategori Dokumen</Label>
        <select 
          id="category-select"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-full p-2.5 bg-white border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0077ff]/50 shadow-sm text-sm"
        >
          <option value="policies">Kebijakan Perusahaan (Policies)</option>
          <option value="technical">Dokumentasi Teknis (Technical)</option>
          <option value="onboarding">Materi Onboarding (Onboarding)</option>
          <option value="reports">Laporan (Reports)</option>
        </select>
      </div>

      <div 
        className={`border-2 border-dashed rounded-xl p-4 sm:p-8 text-center transition-all ${
          isUploading 
            ? "border-blue-500/50 bg-blue-50/50" 
            : "border-slate-300 hover:border-slate-400 bg-slate-50 hover:bg-white"
        }`}
      >
        {isUploading ? (
          <div className="flex flex-col items-center justify-center space-y-3 sm:space-y-4">
            <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
            <div className="w-full max-w-xs bg-slate-200 rounded-full h-2 overflow-hidden">
              <div
                className="bg-[#0077ff] h-full rounded-full transition-all duration-1000"
                style={{ width: uploadPhase === "upload" ? "25%" : uploadPhase === "polling" ? "60%" : "100%" }}
              />
            </div>
            <p className="text-[#0077ff] text-xs sm:text-sm font-medium">
              {uploadPhase === "upload"
                ? "Mengunggah ke server..."
                : uploadPhase === "polling"
                ? "Memproses dokumen di background (ekstraksi & indexing)..."
                : "Menyelesaikan..."}
            </p>
          </div>
        ) : (
          <label className="flex flex-col items-center justify-center cursor-pointer">
              <div className="p-3 bg-slate-100 border border-slate-200 shadow-sm rounded-full mb-3 text-slate-500">
              <UploadCloud className="w-6 h-6 sm:w-8 sm:h-8 text-[#0077ff]" />
            </div>
            <p className="text-sm font-semibold text-slate-800 mb-1">Klik untuk unggah dokumen</p>
            <p className="text-xs text-slate-500 mb-3 sm:mb-4">PDF, DOCX, TXT (Maks 50MB)</p>
              <span className="inline-flex items-center justify-center rounded-md text-sm font-semibold transition-colors border border-slate-200 bg-white text-[#0077ff] hover:bg-[#0077ff]/5 shadow-sm h-9 px-4 py-2 select-none">
              Pilih File
            </span>
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
        <div className={`p-3 sm:p-4 rounded-xl flex items-start space-x-3 text-sm border transition-all ${
          status.type === "success" 
            ? "bg-emerald-50 text-emerald-800 border-emerald-200" 
            : "bg-red-50 text-red-800 border-red-200"
        }`}>
          {status.type === "success" 
            ? <CheckCircle className="w-5 h-5 flex-shrink-0 text-emerald-600" /> 
            : <XCircle className="w-5 h-5 flex-shrink-0 text-red-600" />
          }
          <span className="break-words font-medium text-xs sm:text-sm">{status.message}</span>
        </div>
      )}
    </div>
  );
}
