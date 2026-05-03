"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  type Edge,
  MarkerType,
  type Node,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";
import { Button } from "@/components/ui/button";

const initialNodes: Node[] = [
  { id: "user", position: { x: 260, y: -30 }, data: { label: "User query" } },
  { id: "classify", position: { x: 220, y: 70 }, data: { label: "Classify (Haiku 4.5)" } },
  { id: "dispatch", position: { x: 200, y: 170 }, data: { label: "Dispatch" } },
  { id: "stats", position: { x: 0, y: 280 }, data: { label: "stats_agent" } },
  { id: "calc", position: { x: 160, y: 280 }, data: { label: "calculator_agent" } },
  { id: "lore", position: { x: 320, y: 280 }, data: { label: "lore_agent" } },
  { id: "strategy", position: { x: 480, y: 280 }, data: { label: "strategy_agent" } },
  { id: "verify", position: { x: 220, y: 400 }, data: { label: "verifier_agent" } },
  { id: "synth", position: { x: 220, y: 510 }, data: { label: "synthesizer (Sonnet)" } },
];

const initialEdges: Edge[] = [
  { id: "e0", source: "user", target: "classify", markerEnd: { type: MarkerType.ArrowClosed } },
  { id: "e1", source: "classify", target: "dispatch", markerEnd: { type: MarkerType.ArrowClosed } },
  { id: "e2", source: "dispatch", target: "stats", markerEnd: { type: MarkerType.ArrowClosed } },
  { id: "e3", source: "dispatch", target: "calc", markerEnd: { type: MarkerType.ArrowClosed } },
  { id: "e4", source: "dispatch", target: "lore", markerEnd: { type: MarkerType.ArrowClosed } },
  { id: "e5", source: "dispatch", target: "strategy", markerEnd: { type: MarkerType.ArrowClosed } },
  { id: "e6", source: "stats", target: "verify", markerEnd: { type: MarkerType.ArrowClosed } },
  { id: "e7", source: "calc", target: "verify", markerEnd: { type: MarkerType.ArrowClosed } },
  { id: "e8", source: "lore", target: "verify", markerEnd: { type: MarkerType.ArrowClosed } },
  { id: "e9", source: "strategy", target: "verify", markerEnd: { type: MarkerType.ArrowClosed } },
  { id: "e10", source: "verify", target: "synth", markerEnd: { type: MarkerType.ArrowClosed } },
];

export function AgentGraphModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (params: Parameters<typeof addEdge>[0]) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 h-[80vh] w-[min(960px,94vw)] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-arcana-border bg-arcana-bg p-4 shadow-2xl">
          <div className="mb-2 flex items-center justify-between">
            <Dialog.Title className="text-lg font-semibold text-arcana-gold">
              Grafo LangGraph (vista demo)
            </Dialog.Title>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" className="text-zinc-400">
                <X className="h-5 w-5" />
              </Button>
            </Dialog.Close>
          </div>
          <Dialog.Description className="mb-2 text-xs text-arcana-muted">
            Topología objetivo: classify → dispatch paralelo → verify → synthesize. Arrastra
            para explorar.
          </Dialog.Description>
          <div className="h-[calc(100%-4rem)] rounded-lg border border-arcana-border bg-arcana-surface">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              fitView
              className="rounded-lg"
            >
              <MiniMap />
              <Controls />
              <Background gap={16} color="#2C3140" />
            </ReactFlow>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
