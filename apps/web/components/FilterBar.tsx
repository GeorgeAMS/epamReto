"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { getApiBase } from "@/lib/api";

type Filters = {
  search: string;
  type: string | null;
  generation: number | null;
};

type Generation = {
  id: number;
  name: string;
};

export function FilterBar({
  filters,
  onChange,
}: {
  filters: Filters;
  onChange: (filters: Filters) => void;
}) {
  const [types, setTypes] = useState<string[]>([]);
  const [generations, setGenerations] = useState<Generation[]>([]);

  useEffect(() => {
    fetch(`${getApiBase()}/pokedex/types`)
      .then((res) => res.json())
      .then((data: { types: string[] }) => setTypes(data.types));

    fetch(`${getApiBase()}/pokedex/generations`)
      .then((res) => res.json())
      .then((data: { generations: Generation[] }) => setGenerations(data.generations));
  }, []);

  return (
    <div className="flex flex-wrap gap-4 rounded-lg bg-gray-800 p-4">
      <Input
        placeholder="Buscar Pokemon..."
        value={filters.search}
        onChange={(e) => onChange({ ...filters, search: e.target.value })}
        className="max-w-xs"
      />

      <select
        value={filters.type || ""}
        onChange={(e) => onChange({ ...filters, type: e.target.value || null })}
        className="rounded bg-gray-700 px-3 py-2"
      >
        <option value="">Todos los tipos</option>
        {(types || []).map((type) => (
          <option key={type} value={type} className="capitalize">
            {type}
          </option>
        ))}
      </select>

      <select
        value={filters.generation || ""}
        onChange={(e) =>
          onChange({
            ...filters,
            generation: e.target.value ? parseInt(e.target.value, 10) : null,
          })
        }
        className="rounded bg-gray-700 px-3 py-2"
      >
        <option value="">Todas las generaciones</option>
        {(generations || []).map((gen) => (
          <option key={gen.id} value={gen.id}>
            {gen.name}
          </option>
        ))}
      </select>
    </div>
  );
}
