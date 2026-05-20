import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatSalary(min: number | null, max: number | null, range: string | null): string {
  if (range) return range;
  if (min && max) return `${(min / 1000).toFixed(0)}k - ${(max / 1000).toFixed(0)}k`;
  if (min) return `${(min / 1000).toFixed(0)}k+`;
  return "Not specified";
}
