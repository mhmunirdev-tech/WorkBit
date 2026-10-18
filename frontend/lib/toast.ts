export type ToastVariant = "default" | "success" | "destructive";

export type ToastMessage = {
  id: string;
  title: string;
  description: string;
  variant: ToastVariant;
  duration?: number;
};

const TOAST_STORAGE_KEY = "workbit:queued-toasts";
const listeners = new Set<(toasts: ToastMessage[]) => void>();
let activeToasts: ToastMessage[] = [];

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
  if (activeToasts.some((toast) => toast.variant === input.variant && toast.description === input.description)) {
    return;
  }

  const toast: ToastMessage = {
    id: generateId(),
    ...input,
    duration: input.duration ?? 5000,
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

export function showInvalidFieldToast(target: EventTarget | null) {
  if (
    !(target instanceof HTMLInputElement) &&
    !(target instanceof HTMLTextAreaElement) &&
    !(target instanceof HTMLSelectElement)
  ) {
    return;
  }

  const field = target;
  if (field.validity.valid) return;

  const isEmail = field instanceof HTMLInputElement && field.type === "email";
  const isPassword = field instanceof HTMLInputElement && field.type === "password";
  const description = isEmail
    ? "Enter a valid email address."
    : isPassword && field.validity.tooShort
      ? `Password must be at least ${field.minLength} characters.`
      : field.validity.valueMissing
        ? "Complete this required field."
        : field.validity.patternMismatch
          ? "Enter a value in the required format."
          : "Check the value and try again.";

  showToast({
    title: isEmail ? "Invalid email address" : isPassword ? "Check your password" : "Invalid form value",
    description,
    variant: "destructive",
  });
}

export function dismissToast(id: string) {
  activeToasts = activeToasts.filter((toast) => toast.id !== id);
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
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    sessionStorage.removeItem(TOAST_STORAGE_KEY);
    return [];
  }
}
