"use client";

import { useState } from "react";
import { Loader2, Plus, X } from "lucide-react";
import { Legend, PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getApiBase } from "@/lib/api";

interface PokemonStats {
  name: string;
  types: string[];
  base_stats: {
    hp: number;
    attack: number;
    defense: number;
    special_attack: number;
    special_defense: number;
    speed: number;
    total: number;
  };
  sprite: string;
  ability: string;
}

interface CompareData {
  pokemon: PokemonStats[];
  matchups: Record<string, { stat_advantages: string; type_advantages: string; summary: string }>;
  winner: string;
}

const STAT_COLORS = ["#FCD34D", "#3B82F6", "#10B981", "#EF4444"];

export default function ComparePage() {
  const [pokemonNames, setPokemonNames] = useState(["", ""]);
  const [compareData, setCompareData] = useState<CompareData | null>(null);
  const [loading, setLoading] = useState(false);

  const handleCompare = async () => {
    const validNames = pokemonNames.filter((name) => name.trim());
    if (validNames.length < 2) {
      alert("Please enter at least 2 Pokemon names");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${getApiBase()}/compare/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(validNames.map((name) => name.toLowerCase().trim())),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data: CompareData = await response.json();
      setCompareData(data);
    } catch (error) {
      console.error("Error comparing:", error);
      alert("Failed to compare Pokemon. Please check names and try again.");
    } finally {
      setLoading(false);
    }
  };

  const getRadarData = () => {
    if (!compareData) return [];
    const stats = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"];
    return stats.map((stat) => {
      const dataPoint: Record<string, string | number> = { stat };
      compareData.pokemon.forEach((pokemon) => {
        const statKey = stat === "Atk"
          ? "attack"
          : stat === "Def"
            ? "defense"
            : stat === "SpA"
              ? "special_attack"
              : stat === "SpD"
                ? "special_defense"
                : stat === "Spe"
                  ? "speed"
                  : "hp";
        dataPoint[pokemon.name] = pokemon.base_stats[statKey];
      });
      return dataPoint;
    });
  };

  const addPokemonSlot = () => {
    if (pokemonNames.length < 4) setPokemonNames([...pokemonNames, ""]);
  };

  const removePokemonSlot = (index: number) => {
    if (pokemonNames.length > 2) {
      setPokemonNames(pokemonNames.filter((_, idx) => idx !== index));
    }
  };

  const updatePokemonName = (index: number, value: string) => {
    const next = [...pokemonNames];
    next[index] = value;
    setPokemonNames(next);
  };

  return (
    <div className="container mx-auto space-y-6 p-6">
      <h1 className="text-3xl font-bold text-yellow-400">Compare Pokemon</h1>

      {!compareData && (
        <Card className="border-gray-800 bg-gray-900 p-6">
          <div className="space-y-4">
            <p className="text-sm text-gray-400">Enter 2-4 Pokemon names to compare their stats and matchups</p>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {pokemonNames.map((name, index) => (
                <div key={`slot-${index}`} className="flex gap-2">
                  <Input
                    placeholder={`Pokemon ${index + 1}`}
                    value={name}
                    onChange={(event) => updatePokemonName(index, event.target.value)}
                    onKeyDown={(event) => event.key === "Enter" && void handleCompare()}
                    className="flex-1 border-gray-700 bg-gray-800"
                  />
                  {pokemonNames.length > 2 && (
                    <Button variant="outline" size="icon" onClick={() => removePokemonSlot(index)}>
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>

            <div className="flex gap-4">
              <Button onClick={() => void handleCompare()} disabled={loading || pokemonNames.filter((name) => name.trim()).length < 2}>
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Comparing...
                  </>
                ) : (
                  "Compare"
                )}
              </Button>
              <Button variant="outline" onClick={addPokemonSlot} disabled={pokemonNames.length >= 4}>
                <Plus className="mr-2 h-4 w-4" />
                Add Pokemon
              </Button>
            </div>
          </div>
        </Card>
      )}

      {compareData && (
        <>
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">Comparison Results</h2>
            <Button
              variant="outline"
              onClick={() => {
                setCompareData(null);
                setPokemonNames(["", ""]);
              }}
            >
              New Comparison
            </Button>
          </div>

          <Card className="border-gray-800 bg-gray-900 p-6">
            <h3 className="mb-4 text-xl font-bold text-yellow-400">Stats Comparison</h3>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={getRadarData()}>
                  <PolarGrid stroke="#374151" />
                  <PolarAngleAxis dataKey="stat" stroke="#9CA3AF" />
                  {compareData.pokemon.map((pokemon, index) => (
                    <Radar
                      key={pokemon.name}
                      name={pokemon.name.charAt(0).toUpperCase() + pokemon.name.slice(1)}
                      dataKey={pokemon.name}
                      stroke={STAT_COLORS[index]}
                      fill={STAT_COLORS[index]}
                      fillOpacity={0.3}
                    />
                  ))}
                  <Legend />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {compareData.pokemon.map((pokemon, index) => (
              <Card
                key={pokemon.name}
                className="border-gray-800 bg-gray-900 p-6"
                style={{
                  borderColor: compareData.winner === pokemon.name ? STAT_COLORS[0] : undefined,
                  borderWidth: compareData.winner === pokemon.name ? 2 : 1,
                }}
              >
                <div className="mb-6 flex items-center gap-4">
                  <img src={pokemon.sprite} alt={pokemon.name} className="pixelated h-20 w-20" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h2 className="text-2xl font-bold capitalize">{pokemon.name}</h2>
                      {compareData.winner === pokemon.name && (
                        <Badge className="bg-yellow-400 text-gray-900">Highest BST</Badge>
                      )}
                    </div>
                    <div className="mt-2 flex gap-2">
                      {pokemon.types.map((type) => (
                        <Badge key={type} className={`type-${type}`}>
                          {type.toUpperCase()}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="mb-4 space-y-3">
                  {Object.entries(pokemon.base_stats).map(([stat, value]) => {
                    if (stat === "total") return null;
                    return (
                      <div key={stat} className="flex items-center gap-3">
                        <span className="w-16 text-sm capitalize text-gray-400">
                          {stat.replace("_", " ").replace("special ", "Sp")}
                        </span>
                        <div className="h-6 flex-1 overflow-hidden rounded-full bg-gray-800">
                          <div
                            className="h-full transition-all"
                            style={{
                              width: `${(value / 255) * 100}%`,
                              backgroundColor: STAT_COLORS[index],
                            }}
                          />
                        </div>
                        <span className="w-12 text-right font-mono text-sm">{value}</span>
                      </div>
                    );
                  })}
                </div>

                <div className="border-t border-gray-800 pt-4">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Base Stat Total:</span>
                    <span className="font-mono font-bold">{pokemon.base_stats.total}</span>
                  </div>
                  <div className="mt-2 flex justify-between text-sm">
                    <span className="text-gray-400">Ability:</span>
                    <span className="capitalize">{pokemon.ability.replace(/-/g, " ")}</span>
                  </div>
                </div>
              </Card>
            ))}
          </div>

          {Object.keys(compareData.matchups).length > 0 && (
            <Card className="border-gray-800 bg-gray-900 p-6">
              <h3 className="mb-4 text-xl font-bold text-yellow-400">Matchup Analysis</h3>
              <div className="space-y-4">
                {Object.entries(compareData.matchups).map(([key, matchup]) => {
                  const [name1, name2] = key.split("_vs_");
                  return (
                    <div key={key} className="rounded-lg bg-gray-800 p-4">
                      <h4 className="mb-2 font-semibold capitalize">{name1} vs {name2}</h4>
                      <div className="space-y-1 text-sm text-gray-300">
                        <p><span className="text-gray-400">Stats:</span> {matchup.stat_advantages}</p>
                        <p><span className="text-gray-400">Types:</span> {matchup.type_advantages}</p>
                        <p className="font-medium text-yellow-400">{matchup.summary}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
