"use client";

import { CheckCircle2, CircleAlert, X } from "lucide-react";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";
import { dismissToast, readQueuedToasts, subscribeToToasts, type ToastMessage } from "@/lib/toast";

const variantClasses: Record<ToastMessage["variant"], string> = {
  default: "border-slate-200 bg-white text-slate-900",
  success: "border-emerald-200 bg-emerald-50 text-emerald-950",
  destructive: "border-red-200 bg-red-50 text-red-950",
};

export function Toaster() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    const synced = readQueuedToasts();
    if (synced.length > 0) {
      setToasts((current) => [...synced, ...current]);
    }

    const unsubscribe = subscribeToToasts((next) => setToasts(next));
    return unsubscribe;
  }, []);

  return (
    <div className="pointer-events-none fixed right-4 top-4 z-50 flex w-[min(360px,calc(100vw-2rem))] flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            "pointer-events-auto rounded-xl border px-3.5 py-3 shadow-lg",
            variantClasses[toast.variant],
          )}
          role={toast.variant === "destructive" ? "alert" : "status"}
        >
          <div className="flex items-start gap-2">
            <div className="mt-0.5 shrink-0">
              {toast.variant === "success" && <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden="true" />}
              {toast.variant === "destructive" && <CircleAlert className="h-4 w-4 text-red-600" aria-hidden="true" />}
              {toast.variant === "default" && <div className="h-2 w-2 rounded-full bg-slate-500" aria-hidden="true" />}
            </div>
            <div className="flex-1 space-y-1">
              <p className="text-sm font-semibold leading-5">{toast.title}</p>
              <p className="text-sm leading-5 text-current/80">{toast.description}</p>
            </div>
            <button
              type="button"
              aria-label="Dismiss notification"
              className="ml-1 rounded-md p-1 text-current/70 transition-colors hover:bg-black/5 hover:text-current"
              onClick={() => dismissToast(toast.id)}
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
