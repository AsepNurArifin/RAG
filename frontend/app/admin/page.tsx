"use client";

import { useState } from "react";
import { DocumentTable } from "../../components/admin/DocumentTable";
import { DocumentUploader } from "../../components/admin/DocumentUploader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { motion } from "framer-motion";

export default function KnowledgeVaultPage() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadComplete = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <div className="w-full min-w-0">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6 md:mb-8"
      >
        <h2 className="text-xl md:text-3xl font-bold tracking-tight text-slate-900">Knowledge Vault</h2>
        <p className="text-slate-500 mt-2 text-sm">
          Kelola dokumen internal dan metadata sistem perusahaan.
        </p>
      </motion.div>

      <div className="flex flex-col gap-6 md:gap-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card className="shadow-sm border-slate-200 bg-white overflow-hidden">
            <CardHeader className="border-b border-slate-100 bg-[#f8fafc] pb-4">
              <CardTitle className="text-lg text-slate-900">Daftar Dokumen</CardTitle>
              <CardDescription className="text-slate-500 text-sm">Semua dokumen yang terindeks dalam sistem</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="p-4 md:p-6 overflow-x-auto">
                <DocumentTable refreshTrigger={refreshTrigger} />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Card className="shadow-sm border-slate-200 bg-white overflow-hidden">
            <CardHeader className="border-b border-slate-100 bg-[#f8fafc] pb-4">
              <CardTitle className="text-lg text-slate-900">Unggah Dokumen Baru</CardTitle>
              <CardDescription className="text-slate-500 text-sm truncate">Tambahkan dokumen PDF, Word, atau teks ke dalam Knowledge Vault</CardDescription>
            </CardHeader>
            <CardContent className="p-4 md:p-6">
              <DocumentUploader onUploadComplete={handleUploadComplete} />
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
