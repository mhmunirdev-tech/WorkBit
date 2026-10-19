"use client";

import { Check, CircleAlert, X } from "lucide-react";
import { useEffect, useState, type CSSProperties } from "react";

import { cn } from "@/lib/utils";
import { dismissToast, readQueuedToasts, subscribeToToasts, type ToastMessage } from "@/lib/toast";

const variantClasses: Record<ToastMessage["variant"], string> = {
  default: "workbit-toast-default",
  success: "workbit-toast-success",
  destructive: "workbit-toast-error",
};

export function Toaster() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    const synced = readQueuedToasts();
    if (synced.length > 0) {
      setToasts((current) => [...synced, ...current]);
    }

    const unsubscribe = subscribeToToasts((next) => setToasts(next));
    const timers = synced
      .filter((toast) => toast.duration && toast.duration > 0)
      .map((toast) => window.setTimeout(() => dismissToast(toast.id), toast.duration));
    return () => {
      unsubscribe();
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, []);

  return (
    <div className="workbit-toaster" aria-live="polite" aria-relevant="additions">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn("workbit-toast", variantClasses[toast.variant])}
          role={toast.variant === "destructive" ? "alert" : "status"}
          style={{ "--toast-duration": `${toast.duration ?? 4200}ms` } as CSSProperties}
        >
          <div className="workbit-toast-content">
            <div className="workbit-toast-icon" aria-hidden="true">
              {toast.variant === "success" && <Check size={18} strokeWidth={2.8} />}
              {toast.variant === "destructive" && <CircleAlert size={18} strokeWidth={2.4} />}
            </div>
            <div className="workbit-toast-copy">
              <p className="workbit-toast-title">{toast.title}</p>
              <p className="workbit-toast-description">{toast.description}</p>
            </div>
            <button
              type="button"
              aria-label="Dismiss notification"
              className="workbit-toast-dismiss"
              onClick={() => dismissToast(toast.id)}
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>
          {toast.duration && toast.duration > 0 && <span className="workbit-toast-progress" aria-hidden="true" />}
        </div>
      ))}
    </div>
  );
}
