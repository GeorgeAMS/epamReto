"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Loader2, Save } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getApiBase } from "@/lib/api";

interface TeamMember {
  pokemon: string;
  types: string[];
  ability: string;
  item?: string;
  sprite: string;
  base_stats: {
    hp: number;
    attack: number;
    defense: number;
    special_attack: number;
    special_defense: number;
    speed: number;
    total: number;
  };
}

interface CoverageData {
  team: TeamMember[];
  heatmap: number[][];
  weaknesses: Record<string, number>;
  resistances: Record<string, number>;
}

const ALL_TYPES = [
  "normal", "fire", "water", "electric", "grass", "ice",
  "fighting", "poison", "ground", "flying", "psychic", "bug",
  "rock", "ghost", "dragon", "dark", "steel", "fairy",
];

export default function TeamBuilderPage() {
  const params = useSearchParams();
  const [anchorPokemon, setAnchorPokemon] = useState("");
  const [teamData, setTeamData] = useState<CoverageData | null>(null);
  const [loading, setLoading] = useState(false);
  const [teamName, setTeamName] = useState("");

  const buildTeam = useCallback(async (value?: string) => {
    const anchor = (value ?? anchorPokemon).trim().toLowerCase();
    if (!anchor) return;

    setLoading(true);
    try {
      const response = await fetch(`${getApiBase()}/teams/build`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ anchor_pokemon: anchor, format: "OU", team_size: 6 }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data: CoverageData = await response.json();
      setTeamData(data);
      setTeamName(`${anchor.charAt(0).toUpperCase()}${anchor.slice(1)} Team`);
    } catch (error) {
      console.error("Error building team:", error);
      alert("Failed to build team. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [anchorPokemon]);

  useEffect(() => {
    const anchorFromQuery = params.get("anchor");
    if (anchorFromQuery) {
      setAnchorPokemon(anchorFromQuery);
      void buildTeam(anchorFromQuery);
    }
  }, [params, buildTeam]);

  const saveTeam = async () => {
    if (!teamData || !teamName.trim()) return;
    try {
      const response = await fetch(`${getApiBase()}/saved-teams/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: teamName,
          format: "OU",
          members: teamData.team.map((member) => ({
            pokemon: member.pokemon,
            sprite: member.sprite,
            types: member.types,
            ability: member.ability,
            item: member.item ?? null,
          })),
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      alert("Team saved successfully!");
    } catch (error) {
      console.error("Error saving team:", error);
      alert("Failed to save team.");
    }
  };

  const getHeatmapColor = (value: number): string => {
    if (value === 0) return "bg-gray-900";
    if (value < 0.5) return "bg-green-700";
    if (value === 0.5) return "bg-green-600";
    if (value === 1.0) return "bg-yellow-600";
    if (value === 2.0) return "bg-orange-600";
    if (value > 2.0) return "bg-red-600";
    return "bg-gray-700";
  };

  return (
    <div className="container mx-auto space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-yellow-400">Team Builder</h1>
        {teamData && (
          <div className="flex gap-2">
            <Button onClick={saveTeam} disabled={!teamName.trim()}>
              <Save className="mr-2 h-4 w-4" />
              Save Team
            </Button>
            <Button variant="outline" onClick={() => setTeamData(null)}>
              Clear
            </Button>
          </div>
        )}
      </div>

      {!teamData && (
        <Card className="border-gray-800 bg-gray-900 p-6">
          <div className="space-y-4">
            <div>
              <label className="mb-2 block text-sm font-medium">Anchor Pokemon</label>
              <p className="mb-3 text-sm text-gray-400">
                Enter a Pokemon to build a team around (e.g., Garchomp, Dragapult, Tyranitar)
              </p>
              <div className="flex gap-4">
                <Input
                  placeholder="Enter Pokemon name..."
                  value={anchorPokemon}
                  onChange={(e) => setAnchorPokemon(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && void buildTeam()}
                  className="flex-1 border-gray-700 bg-gray-800"
                />
                <Button onClick={() => void buildTeam()} disabled={!anchorPokemon.trim() || loading}>
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Building...
                    </>
                  ) : (
                    "Build Team"
                  )}
                </Button>
              </div>
            </div>
          </div>
        </Card>
      )}

      {teamData && (
        <>
          <Card className="border-gray-800 bg-gray-900 p-4">
            <Input
              placeholder="Team Name (e.g., OU Hyper Offense)"
              value={teamName}
              onChange={(e) => setTeamName(e.target.value)}
              className="border-gray-700 bg-gray-800"
            />
          </Card>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {teamData.team.map((member) => (
              <Card key={member.pokemon} className="border-gray-800 bg-gray-900 p-4 transition-colors hover:border-yellow-400/50">
                <div className="space-y-3">
                  <div className="flex justify-center">
                    <img src={member.sprite} alt={member.pokemon} className="pixelated h-24 w-24" />
                  </div>

                  <h3 className="text-center text-xl font-bold capitalize">{member.pokemon}</h3>

                  <div className="flex justify-center gap-2">
                    {member.types.map((type) => (
                      <Badge key={type} className={`type-${type} px-3 py-1 text-xs`}>
                        {type.toUpperCase()}
                      </Badge>
                    ))}
                  </div>

                  <div className="space-y-1 text-sm text-gray-300">
                    <p>
                      <span className="text-gray-400">Ability:</span>{" "}
                      <span className="capitalize">{member.ability.replace(/-/g, " ")}</span>
                    </p>
                    {member.item && (
                      <p>
                        <span className="text-gray-400">Item:</span>{" "}
                        <span className="capitalize">{member.item.replace(/-/g, " ")}</span>
                      </p>
                    )}
                    <p>
                      <span className="text-gray-400">BST:</span> {member.base_stats.total}
                    </p>
                  </div>
                </div>
              </Card>
            ))}
          </div>

          <Card className="border-gray-800 bg-gray-900 p-6">
            <h2 className="mb-4 text-xl font-bold text-yellow-400">Type Coverage Analysis</h2>

            <div className="mb-6 grid grid-cols-1 gap-6 md:grid-cols-2">
              <div>
                <h3 className="mb-3 text-lg font-semibold text-red-400">Team Weaknesses</h3>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(teamData.weaknesses).sort(([, a], [, b]) => b - a).map(([type, count]) => (
                    <Badge key={type} className={`type-${type}`}>
                      {type.toUpperCase()} ({count})
                    </Badge>
                  ))}
                  {Object.keys(teamData.weaknesses).length === 0 && (
                    <p className="text-sm text-gray-400">No major weaknesses!</p>
                  )}
                </div>
              </div>
              <div>
                <h3 className="mb-3 text-lg font-semibold text-green-400">Team Resistances</h3>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(teamData.resistances).sort(([, a], [, b]) => b - a).map(([type, count]) => (
                    <Badge key={type} className={`type-${type}`}>
                      {type.toUpperCase()} ({count})
                    </Badge>
                  ))}
                  {Object.keys(teamData.resistances).length === 0 && (
                    <p className="text-sm text-gray-400">No major resistances</p>
                  )}
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <div className="inline-block min-w-full text-xs font-mono">
                <div className="mb-2 flex">
                  <div className="w-16" />
                  {teamData.team.map((member) => (
                    <div key={member.pokemon} className="w-12 truncate text-center capitalize" title={member.pokemon}>
                      {member.pokemon.slice(0, 3)}
                    </div>
                  ))}
                </div>
                {teamData.heatmap.map((row, typeIdx) => (
                  <div key={ALL_TYPES[typeIdx]} className="mb-1 flex">
                    <div className="w-16 pr-2 text-right capitalize text-gray-400">{ALL_TYPES[typeIdx]}</div>
                    {row.map((value, memberIdx) => (
                      <div
                        key={`${ALL_TYPES[typeIdx]}-${teamData.team[memberIdx].pokemon}`}
                        className={`flex h-8 w-12 items-center justify-center border border-gray-800 ${getHeatmapColor(value)}`}
                        title={`${ALL_TYPES[typeIdx]} -> ${teamData.team[memberIdx].pokemon}: ${value}x`}
                      >
                        {value === 0 ? "0" : value.toFixed(1)}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

