export type ToastVariant = "default" | "success" | "destructive";
export type ToastKind =
  | "login-error"
  | "login-success"
  | "otp-sent"
  | "payout-account-saved"
  | "payout-account-removed"
  | "withdrawal-requested"
  | "withdrawal-pending"
  | "withdrawal-paid"
  | "package-payment-submitted"
  | "package-activated";

export type ToastMessage = {
  id: string;
  title: string;
  description: string;
  variant: ToastVariant;
  kind?: ToastKind;
  duration?: number;
  expiresAt?: number;
};

const TOAST_STORAGE_KEY = "workbit:queued-toasts";
const listeners = new Set<(toasts: ToastMessage[]) => void>();
let activeToasts: ToastMessage[] = [];
const allowedToastKinds = new Set<ToastKind>([
  "login-error",
  "login-success",
  "otp-sent",
  "payout-account-saved",
  "payout-account-removed",
  "withdrawal-requested",
  "withdrawal-pending",
  "withdrawal-paid",
  "package-payment-submitted",
  "package-activated",
]);

function notify() {
  listeners.forEach((listener) => listener(activeToasts));
}

function generateId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function showToast(input: Omit<ToastMessage, "id">) {
  if (!input.kind || !allowedToastKinds.has(input.kind)) return;

  if (activeToasts.some((toast) => toast.variant === input.variant && toast.description === input.description)) {
    return;
  }

  const toast: ToastMessage = {
    id: generateId(),
    ...input,
    duration: input.duration ?? 4200,
    expiresAt: input.duration === 0 ? undefined : Date.now() + (input.duration ?? 4200),
  };

  activeToasts = [toast, ...activeToasts].slice(0, 4);
  notify();

  if (typeof window !== "undefined") {
    try {
      const queued = readQueuedToasts();
      queued.push(toast);
      sessionStorage.setItem(TOAST_STORAGE_KEY, JSON.stringify(queued));
    } catch {
      // Ignore storage failures and keep the in-memory toast visible.
    }
  }

  if (toast.duration && toast.duration > 0) {
    window.setTimeout(() => dismissToast(toast.id), toast.duration);
  }
}

export function dismissToast(id: string) {
  activeToasts = activeToasts.filter((toast) => toast.id !== id);
  if (typeof window !== "undefined") {
    try {
      const queued = readQueuedToasts();
      if (queued.length > 0) {
        sessionStorage.setItem(
          TOAST_STORAGE_KEY,
          JSON.stringify(queued.filter((toast) => toast.id !== id)),
        );
      }
    } catch {
      // Keep dismissal functional when session storage is unavailable.
    }
  }
  notify();
}

export function subscribeToToasts(listener: (toasts: ToastMessage[]) => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function readQueuedToasts(): ToastMessage[] {
  if (typeof window === "undefined") return [];

  try {
    const raw = sessionStorage.getItem(TOAST_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ToastMessage[];
    sessionStorage.removeItem(TOAST_STORAGE_KEY);
    if (!Array.isArray(parsed)) return [];
    const now = Date.now();
    return parsed
      .filter(
        (toast): toast is ToastMessage =>
          Boolean(
            toast &&
              toast.kind &&
              allowedToastKinds.has(toast.kind) &&
              (toast.expiresAt === undefined || toast.expiresAt > now),
          ),
      )
      .map((toast) =>
        toast.expiresAt === undefined
          ? toast
          : { ...toast, duration: Math.max(0, toast.expiresAt - now) },
      );
  } catch {
    sessionStorage.removeItem(TOAST_STORAGE_KEY);
    return [];
  }
}
