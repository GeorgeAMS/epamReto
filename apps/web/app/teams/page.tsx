"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Download, Loader2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getApiBase } from "@/lib/api";

interface TeamMember {
  pokemon: string;
  sprite: string;
  types: string[];
  ability: string;
  item?: string;
}

interface SavedTeam {
  id: string;
  name: string;
  format: string;
  members: TeamMember[];
  created_at: string;
  updated_at: string;
}

export default function TeamsPage() {
  const router = useRouter();
  const [teams, setTeams] = useState<SavedTeam[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void fetchTeams();
  }, []);

  const fetchTeams = async () => {
    try {
      const response = await fetch(`${getApiBase()}/saved-teams/`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data: SavedTeam[] = await response.json();
      setTeams(data);
    } catch (error) {
      console.error("Error fetching teams:", error);
    } finally {
      setLoading(false);
    }
  };

  const deleteTeam = async (teamId: string) => {
    if (!confirm("Are you sure you want to delete this team?")) return;
    try {
      const response = await fetch(`${getApiBase()}/saved-teams/${teamId}`, { method: "DELETE" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await fetchTeams();
    } catch (error) {
      console.error("Error deleting team:", error);
      alert("Failed to delete team");
    }
  };

  const exportTeam = async (teamId: string) => {
    try {
      const response = await fetch(`${getApiBase()}/saved-teams/${teamId}/export`, { method: "POST" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data: { content: string } = await response.json();
      await navigator.clipboard.writeText(data.content);
      alert("Team exported to clipboard in Showdown format!");
    } catch (error) {
      console.error("Error exporting team:", error);
      alert("Failed to export team");
    }
  };

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-yellow-400" />
      </div>
    );
  }

  return (
    <div className="container mx-auto space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-yellow-400">My Teams</h1>
        <Button onClick={() => router.push("/teams/builder")}>+ New Team</Button>
      </div>

      <div className="space-y-4">
        {teams.length === 0 ? (
          <Card className="border-gray-800 bg-gray-900 p-12 text-center">
            <p className="mb-4 text-lg text-gray-400">No teams saved yet</p>
            <p className="mb-6 text-sm text-gray-500">
              Build your first competitive team and save it here
            </p>
            <Button onClick={() => router.push("/teams/builder")}>Create Your First Team</Button>
          </Card>
        ) : (
          teams.map((team) => (
            <Card key={team.id} className="border-gray-800 bg-gray-900 p-6 transition-colors hover:border-yellow-400/50">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="mb-4 flex items-center gap-4">
                    <h3 className="text-xl font-bold">{team.name}</h3>
                    <span className="rounded-full bg-yellow-400/10 px-3 py-1 text-sm font-medium text-yellow-400">
                      {team.format}
                    </span>
                    <span className="text-sm text-gray-500">
                      {new Date(team.updated_at).toLocaleDateString()}
                    </span>
                  </div>

                  <div className="flex gap-2">
                    {team.members.map((member) => (
                      <div
                        key={`${team.id}-${member.pokemon}`}
                        className="relative h-16 w-16 overflow-hidden rounded-lg bg-gray-800 transition-all hover:ring-2 hover:ring-yellow-400"
                        title={member.pokemon}
                      >
                        <img src={member.sprite} alt={member.pokemon} className="pixelated h-full w-full object-contain" />
                      </div>
                    ))}
                    {Array.from({ length: Math.max(0, 6 - team.members.length) }).map((_, index) => (
                      <div key={`empty-${team.id}-${index}`} className="h-16 w-16 rounded-lg border-2 border-dashed border-gray-700 bg-gray-800/50" />
                    ))}
                  </div>
                </div>

                <div className="ml-4 flex gap-2">
                  <Button variant="outline" size="icon" onClick={() => void exportTeam(team.id)} title="Export to Showdown">
                    <Download className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => void deleteTeam(team.id)}
                    title="Delete team"
                    className="hover:border-red-500 hover:bg-red-900/20"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
