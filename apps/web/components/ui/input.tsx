import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(({ className, type, ...props }, ref) => (
  <input
    type={type}
    className={cn(
      "flex h-10 w-full rounded-md border border-arcana-border bg-arcana-bg px-3 py-2 text-sm text-zinc-100",
      "placeholder:text-arcana-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcana-ball",
      "disabled:cursor-not-allowed disabled:opacity-50",
      className,
    )}
    ref={ref}
    {...props}
  />
));
Input.displayName = "Input";

export { Input };
