"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[400px] flex items-center justify-center p-8">
          <div className="max-w-md w-full bg-error-container text-on-error-container p-6 rounded-2xl shadow-xl border border-error/20 flex flex-col items-center text-center">
            <div className="w-16 h-16 bg-error/10 rounded-full flex items-center justify-center mb-4 text-error">
              <AlertTriangle className="w-8 h-8" />
            </div>
            <h2 className="text-xl font-bold mb-2 font-display">System Malfunction</h2>
            <p className="text-sm opacity-80 mb-6 font-body">
              EnterpriseMind UI encountered an unexpected error. 
              {this.state.error && (
                <span className="block mt-2 font-mono text-xs opacity-70 break-all bg-black/10 p-2 rounded">
                  {this.state.error.message}
                </span>
              )}
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false });
                window.location.reload();
              }}
              className="flex items-center gap-2 bg-error text-on-error px-6 py-2.5 rounded-full font-medium hover:bg-error/90 transition-colors shadow-lg shadow-error/20"
            >
              <RefreshCcw className="w-4 h-4" />
              <span>Reload Interface</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
