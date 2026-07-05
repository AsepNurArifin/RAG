"use client";

import { useState } from "react";
import { DocumentTable } from "../../components/admin/DocumentTable";
import { DocumentUploader } from "../../components/admin/DocumentUploader";

export default function KnowledgeVaultPage() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadComplete = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <div className="w-full max-w-6xl mx-auto py-8">
      <div className="mb-6 flex justify-between items-end">
        <div>
          <h2 className="font-h3 text-h3 text-on-surface">Knowledge Vault</h2>
          <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
            Manage your internal documents and metadata.
          </p>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-surface-container border-instrument rounded p-6">
            <DocumentTable refreshTrigger={refreshTrigger} />
          </div>
        </div>
        
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-surface-container border-instrument rounded p-6">
            <h3 className="font-data-label text-data-label text-outline mb-4 uppercase tracking-wider">
              Upload Document
            </h3>
            <DocumentUploader onUploadComplete={handleUploadComplete} />
          </div>
        </div>
      </div>
    </div>
  );
}
