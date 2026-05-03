"use client";

import type { ReactNode } from "react";
import * as Popover from "@radix-ui/react-popover";
import type { Source } from "@/lib/types";
import { cn } from "@/lib/utils";

type Props = {
  index: number;
  source?: Source;
  children: ReactNode;
  className?: string;
};

export function CitationPopover({ index, source, children, className }: Props) {
  if (!source) {
    return (
      <span className={cn("text-arcana-muted cursor-default", className)} title="Fuente pendiente">
        {children}
      </span>
    );
  }

  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex cursor-pointer items-baseline border-b border-dotted border-arcana-gold font-mono text-xs text-arcana-gold hover:brightness-110",
            className,
          )}
        >
          {children}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className="z-50 w-72 rounded-lg border border-arcana-border bg-arcana-surface p-3 text-sm shadow-xl"
          sideOffset={6}
        >
          <p className="font-mono text-xs text-arcana-gold">[{index}] {source.title}</p>
          {source.url ? (
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="mt-1 block truncate text-xs text-sky-400 underline"
            >
              {source.url}
            </a>
          ) : null}
          {source.snippet ? (
            <p className="mt-2 max-h-32 overflow-y-auto text-xs text-zinc-300">{source.snippet}</p>
          ) : null}
          <p className="mt-2 text-[10px] uppercase tracking-wide text-arcana-muted">
            {source.kind ?? "source"}
          </p>
          <Popover.Arrow className="fill-arcana-border" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
