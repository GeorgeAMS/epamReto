import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { ApiError, api } from "@/lib/api/client";
import { setAuthToken } from "@/lib/auth";
import { requireGuest } from "@/lib/route-guards";

export const Route = createFileRoute("/login")({
  beforeLoad: requireGuest,
  head: () => ({
    meta: [
      { title: "Login — Pokédex Arcana" },
      { name: "description", content: "Acceso a la app Pokédex Arcana." },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const out = await api.login({ username: username.trim(), password });
      setAuthToken(out.access_token);
      navigate({ to: "/" });
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "No se pudo iniciar sesión";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-4.5rem)] w-full max-w-md items-center px-4">
      <form
        onSubmit={onSubmit}
        className="w-full rounded-2xl border-[3px] border-poke-black bg-poke-white p-5 shadow-[0_5px_0_0_var(--poke-black)]"
      >
        <div className="font-pixel text-[9px] uppercase text-poke-blue">acceso seguro</div>
        <h1 className="mt-2 font-display text-3xl font-bold text-poke-black">
          Entrar a <span className="text-poke-red">Pokédex Arcana</span>
        </h1>
        <label className="mt-5 block text-xs font-bold text-poke-black">Usuario</label>
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          autoComplete="username"
          className="mt-1 w-full rounded-xl border-[3px] border-poke-black bg-poke-cream px-3 py-2 text-sm text-poke-black outline-none"
        />
        <label className="mt-4 block text-xs font-bold text-poke-black">Contraseña</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
          className="mt-1 w-full rounded-xl border-[3px] border-poke-black bg-poke-cream px-3 py-2 text-sm text-poke-black outline-none"
        />
        {error ? <p className="mt-3 text-xs font-bold text-poke-red">{error}</p> : null}
        <button
          type="submit"
          disabled={loading}
          className="mt-5 w-full rounded-full border-[3px] border-poke-black bg-poke-red px-4 py-2 font-bold text-poke-white shadow-[0_3px_0_0_var(--poke-black)] disabled:opacity-70"
        >
          {loading ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </div>
  );
}

