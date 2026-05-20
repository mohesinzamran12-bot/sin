"use client";

import { useRef, useState } from "react";
import { Upload, FileText, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import type { Candidate } from "@/types";

interface CvUploaderProps {
  candidateId: string;
  currentCvPath: string | null;
  wordCount?: number | null;
  onUploadSuccess: (candidate: Candidate) => void;
}

export function CvUploader({
  candidateId,
  currentCvPath,
  wordCount,
  onUploadSuccess,
}: CvUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      toast.error("Only PDF files are accepted");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setUploading(true);
    try {
      const updated = await api.upload<Candidate>(
        `/api/v1/candidates/${candidateId}/cv`,
        formData
      );
      onUploadSuccess(updated);
      toast.success("CV uploaded and processed successfully");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  const cvFilename = currentCvPath
    ? currentCvPath.split("/").pop()
    : null;

  return (
    <div className="space-y-3">
      {currentCvPath && (
        <div className="flex items-center gap-2 p-3 bg-muted rounded-md">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <div>
            <p className="text-sm font-medium">{cvFilename}</p>
            {wordCount && (
              <p className="text-xs text-muted-foreground">
                {wordCount.toLocaleString()} words extracted
              </p>
            )}
          </div>
        </div>
      )}

      <div
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          dragOver
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50"
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <FileText className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
        <p className="text-sm text-muted-foreground mb-3">
          {currentCvPath ? "Replace CV" : "Upload your CV"}
        </p>
        <p className="text-xs text-muted-foreground mb-3">
          Drag & drop a PDF, or click to browse
        </p>
        <Button
          variant="outline"
          size="sm"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          <Upload className="h-4 w-4 mr-2" />
          {uploading ? "Uploading..." : "Choose PDF"}
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="hidden"
          onChange={handleChange}
        />
      </div>
    </div>
  );
}
