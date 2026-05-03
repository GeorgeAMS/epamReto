"use client";

import ExplorePage from "@/app/explore/page";
import ChatPage from "@/app/chat/page";
import ComparePage from "@/app/compare/page";
import TeamsPage from "@/app/teams/page";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-gray-800 p-4">
        <div className="container mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-arcana-gold">
              <span className="text-2xl">⚡</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-arcana-gold">POKEDEX ARCANA</h1>
              <p className="text-xs text-gray-400">AI-Powered Pokemon Encyclopedia</p>
            </div>
          </div>
        </div>
      </header>

      <Tabs defaultValue="explore" className="container mx-auto py-6">
        <TabsList className="mb-6 grid h-auto w-full grid-cols-2 gap-1 sm:grid-cols-4">
          <TabsTrigger value="explore">🔍 Explorar</TabsTrigger>
          <TabsTrigger value="chat">💬 Chat IA</TabsTrigger>
          <TabsTrigger value="compare">⚖️ Comparar</TabsTrigger>
          <TabsTrigger value="teams">👥 Equipos</TabsTrigger>
        </TabsList>

        <TabsContent value="explore">
          <ExplorePage />
        </TabsContent>

        <TabsContent value="chat">
          <ChatPage />
        </TabsContent>

        <TabsContent value="compare">
          <ComparePage />
        </TabsContent>

        <TabsContent value="teams">
          <TeamsPage />
        </TabsContent>
      </Tabs>
    </div>
  );
}
