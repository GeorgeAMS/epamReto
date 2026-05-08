import { Link, useNavigate } from "@tanstack/react-router";
import { MessageSquare, Search, Swords, Columns2, LogOut } from "lucide-react";
import { clearAuthToken, getAuthToken } from "@/lib/auth";

const items = [
  { to: "/", label: "Chat", icon: MessageSquare, exact: true },
  { to: "/explore", label: "Pokédex", icon: Search, exact: false },
  { to: "/team", label: "Equipo", icon: Swords, exact: false },
  { to: "/compare", label: "Comparar", icon: Columns2, exact: false },
] as const;

function PokeballIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
      <circle cx="32" cy="32" r="29" fill="#fff" stroke="#1a1a1a" strokeWidth="4" />
      <path d="M3 32 a29 29 0 0 1 58 0 z" fill="var(--poke-red)" stroke="#1a1a1a" strokeWidth="4" />
      <line x1="3" y1="32" x2="61" y2="32" stroke="#1a1a1a" strokeWidth="4" />
      <circle cx="32" cy="32" r="8" fill="#fff" stroke="#1a1a1a" strokeWidth="4" />
      <circle cx="32" cy="32" r="3" fill="#1a1a1a" />
    </svg>
  );
}

export function TopNav() {
  const navigate = useNavigate();
  const isAuthed = Boolean(getAuthToken());

  return (
    <header className="sticky top-0 z-40">
      {/* Banda roja superior estilo Pokédex */}
      <div className="h-2 bg-poke-red border-b-2 border-poke-black" />
      <div className="bg-poke-cream/95 backdrop-blur-md border-b-[3px] border-poke-black">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4">
          <Link to="/" className="flex items-center gap-3 group">
            <PokeballIcon className="h-10 w-10 group-hover:pokeball-shake drop-shadow-[0_3px_0_rgba(0,0,0,1)]" />
            <div className="leading-none">
              <div className="font-display text-xl font-bold tracking-tight text-poke-black">
                Pokédex <span className="text-poke-red">Arcana</span>
              </div>
              <div className="font-pixel text-[8px] text-poke-blue mt-1">// AI TRAINER ASSIST</div>
            </div>
          </Link>

          <nav className="flex items-center gap-1 rounded-full bg-poke-white border-[3px] border-poke-black p-1 shadow-[0_3px_0_0_var(--poke-black)]">
            {items.map((it) => (
              <Link
                key={it.to}
                to={it.to}
                activeOptions={{ exact: it.exact }}
                className="px-3 py-1.5 rounded-full text-xs sm:text-sm font-bold text-poke-black/70 hover:text-poke-black transition-all flex items-center gap-1.5 data-[status=active]:bg-poke-red data-[status=active]:text-poke-white data-[status=active]:shadow-[inset_0_-2px_0_0_var(--poke-red-dark)]"
              >
                <it.icon className="h-3.5 w-3.5" strokeWidth={2.5} />
                <span className="hidden sm:inline">{it.label}</span>
              </Link>
            ))}
          </nav>

          <div className="hidden md:flex items-center gap-2">
            <div className="flex items-center gap-2 rounded-full bg-poke-white border-2 border-poke-black px-3 py-1 shadow-[0_2px_0_0_var(--poke-black)]">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-emerald-200 animate-pulse" />
              <span className="font-pixel text-[9px] text-poke-black">ONLINE</span>
            </div>
            {isAuthed ? (
              <button
                onClick={() => {
                  clearAuthToken();
                  navigate({ to: "/login" });
                }}
                className="inline-flex items-center gap-1 rounded-full border-[3px] border-poke-black bg-poke-white px-3 py-1 text-xs font-bold text-poke-black shadow-[0_2px_0_0_var(--poke-black)] hover:bg-poke-yellow"
              >
                <LogOut className="h-3.5 w-3.5" strokeWidth={2.5} />
                Salir
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}
