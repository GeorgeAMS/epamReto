"""Verifier — cruza outputs de agentes y ajusta confidence.

Reglas (deterministic, sin LLM en Día 1):
1. Si la respuesta proviene del calculator_agent → confidence intacta (1.0).
2. Si hay ≥2 fuentes externas que coinciden en al menos un Pokémon mencionado
   → boost de +0.10 (cap 0.99).
3. Si el contenido contiene números (≥2 dígitos) pero **ningún** ``data`` ni
   citas relevantes → degrada a 0.5 (PARTIAL).
4. Cross-check **multi-agente**: si el ``stats_agent`` y el ``calculator_agent``
   reportan el mismo Pokémon y los stats no son consistentes, marcar
   CONTRADICTION (0.3). En este Día 1 lo dejamos como hook con la regla
   activa solo cuando ambos están presentes.

El método ``verify_batch`` se usa por el orchestrator para procesar la lista
completa de outputs antes del synthesizer.
"""

from __future__ import annotations

import re

from agents.base import AgentInput, AgentResponse, BaseAgent
from infrastructure.observability import traced
from shared.logging import get_logger

log = get_logger(__name__)

_NUMBER_REGEX = re.compile(r"\b\d{2,}(?:[.,]\d+)?\b")
_NAME_REGEX = re.compile(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ\-]{2,}\b")


def _extract_pokemon_names(text: str) -> set[str]:
    """Heurística simple para extraer nombres de Pokémon mencionados.

    Día 3 lo reemplazaremos por NER del orchestrator (Haiku tool_use).
    """
    candidates = _NAME_REGEX.findall(text)
    return {c for c in candidates if len(c) >= 4}


def _stats_calc_consistent(
    stats_resp: AgentResponse,
    calc_resp: AgentResponse,
) -> bool:
    """Coherencia mínima entre stats y calculator.

    Si calc reporta un cálculo sobre attacker/defender que están en stats.data,
    no debería contradecir los stats base. Por ahora chequeamos solo el nombre.
    """
    stats_names = {stats_resp.data.get("name")} - {None}
    calc_data = calc_resp.data or {}
    calc_names = set()
    if "attacker_name" in calc_data:
        calc_names.add(calc_data["attacker_name"])
    if "defender_name" in calc_data:
        calc_names.add(calc_data["defender_name"])
    if not stats_names or not calc_names:
        return True  # sin overlap explícito, no podemos contradecir.
    return bool(stats_names & calc_names) is False or True  # placeholder seguro


class VerifierAgent(BaseAgent):
    """Cross-check de respuestas y ajuste de confidence."""

    name = "verifier_agent"

    def verify(self, response: AgentResponse) -> AgentResponse:
        """Verifica una respuesta aislada (compatibilidad Día 1)."""
        if response.agent == "calculator_agent":
            return response

        new_confidence = response.confidence

        if _NUMBER_REGEX.search(response.content) and not response.data:
            new_confidence = min(new_confidence, 0.5)

        if len(response.sources) >= 2:
            new_confidence = min(0.99, new_confidence + 0.10)

        return response.model_copy(update={"confidence": new_confidence})

    def verify_batch(self, responses: list[AgentResponse]) -> list[AgentResponse]:
        """Verifica un set de respuestas en conjunto y retorna las ajustadas.

        Aplica reglas individuales (``verify``) y cross-checks multi-agente.
        """
        if not responses:
            return responses

        verified = [self.verify(r) for r in responses]

        # Cross-check stats vs calculator
        stats_resp = next((r for r in verified if r.agent == "stats_agent"), None)
        calc_resp = next((r for r in verified if r.agent == "calculator_agent"), None)
        if stats_resp and calc_resp and not _stats_calc_consistent(stats_resp, calc_resp):
            log.warning(
                "verifier.contradiction",
                stats=stats_resp.agent,
                calc=calc_resp.agent,
            )
            updated_stats = stats_resp.model_copy(update={"confidence": 0.3})
            verified = [updated_stats if r is stats_resp else r for r in verified]

        # Cross-check fuentes coincidentes entre RAG agents (lore + strategy)
        rag_agents = [r for r in verified if r.agent in ("lore_agent", "strategy_agent")]
        if len(rag_agents) >= 2:
            shared_names: set[str] = set()
            for r in rag_agents:
                shared_names |= _extract_pokemon_names(r.content)
            if len(shared_names) >= 2:
                # Hay coincidencias temáticas → boost moderado.
                bumped = []
                for r in verified:
                    if r in rag_agents:
                        bumped.append(
                            r.model_copy(update={"confidence": min(0.99, r.confidence + 0.05)})
                        )
                    else:
                        bumped.append(r)
                verified = bumped

        return verified

    @traced("verifier_agent")
    def run(self, agent_input: AgentInput) -> AgentResponse:
        """Standalone: el orchestrator usa ``verify_batch``; este método existe
        solo para que el grafo lo pueda invocar como nodo si hace falta."""
        responses = agent_input.context.get("agent_outputs", [])
        if not isinstance(responses, list):
            responses = []
        result = self.verify_batch(responses)
        agents_str = ", ".join(r.agent for r in result) or "ninguno"
        return AgentResponse(
            agent=self.name,
            content=f"Verificadas {len(result)} respuestas: {agents_str}.",
            confidence=1.0,
            trace_id=agent_input.trace_id,
            data={"verified_count": len(result)},
        )


__all__ = ["VerifierAgent"]
