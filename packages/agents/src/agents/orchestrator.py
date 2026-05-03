"""Orchestrator — grafo LangGraph multi-agente.

Topología::

    START → classify_intent (Haiku tool_use) → dispatch_agents
                                                    │
            (intent ∈ {stats, calc, lore, strategy, mixed})
                                                    │
                ┌───────────────┬───────────────────┼───────────────┬───────────────┐
                ▼               ▼                   ▼               ▼               ▼
         stats_agent      calculator_agent      lore_agent      strategy_agent
                └───────────────┴───────────────────┴───────────────┴───────────────┘
                                                    │
                                                    ▼
                                            verifier_node
                                                    │
                                                    ▼
                                            synthesizer_node → END

Decisiones:
- ``dispatch_agents`` corre uno o varios agentes en una sola pasada
  (sequential dentro del nodo) → simpler que LangGraph parallel API y permite
  streaming claro luego.
- Backward compat: la firma pública ``Orchestrator.handle(query, trace_id)``
  se mantiene 1:1 — nada en la API se rompe al swap.
- Streaming: ``handle_stream(query, trace_id)`` corre el grafo hasta verify y
  luego usa ``Synthesizer.stream`` para emitir tokens reales.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from enum import Enum
import re
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from agents.base import AgentInput, AgentResponse
from agents.calculator_agent import CalculatorAgent, CalculatorRequest
from agents.lore_agent import LoreAgent
from agents.stats_agent import StatsAgent
from agents.strategy_agent import StrategyAgent
from agents.synthesizer import Synthesizer
from agents.verifier_agent import VerifierAgent
from infrastructure.llm_client import LLMClient, get_llm_client
from infrastructure.pokeapi_client import PokeAPIClient, get_client
from domain.pokemon.value_objects import EVs, Nature
from shared.errors import AgentError
from shared.logging import get_logger
from shared.types import Source, TraceId

log = get_logger(__name__)

# Lista Pokémon comunes para validación
COMMON_POKEMON = [
    "dragapult", "landorus-therian", "corviknight", "ferrothorn", "heatran",
    "toxapex", "rillaboom", "kartana", "tornadus-therian", "clefable",
    "pikachu", "charizard", "mewtwo", "bulbasaur", "squirtle",
    "charmander", "jigglypuff", "snorlax", "dragonite", "gengar",
    "lucario", "garchomp", "greninja", "tyranitar", "gyarados", "rayquaza", "kyogre",
    "groudon", "dialga", "palkia", "giratina", "arceus",
    "blaziken", "swampert", "sceptile", "infernape", "empoleon",
    "torterra", "serperior", "samurott", "emboar", "greninja",
]

# Palabras inglesas / español en prompts de team building (no son Pokémon).
_EXTRACT_STOPWORDS = frozenset(
    {
        "recommend", "recomienda", "teammates", "teammate", "compañeros", "compañero",
        "which", "what", "when", "where", "para", "equipo",
        "build", "competitive", "team", "teams", "weaknesses", "weakness",
        "covering", "cover", "they", "that", "this", "with", "from", "your",
        "have", "does", "would", "could", "should", "about", "into", "their",
        "make", "give", "list", "best", "five", "mates", "mate", "tipos", "tipo",
    }
)

# Team building / Smogon — detección por palabras y frases ("en ou" cubre "... en OU").
_STRATEGY_KEYWORDS = (
    "recomienda",
    "recommend",
    "recomendación",
    "teammates",
    "teammate",
    "compañeros",
    "compañero",
    "equipo",
    "team",
    "squad",
    "ou",
    "sinergía",
    "synergy",
    "debilidades",
    "cubrir",
    "weaknesses",
    "weakness",
    "cover",
    "build me",
    "build",
    "construir",
    "armar",
    "team building",
    "cobertura",
    "coverage",
    "competitivo",
    "competitive",
    "moveset",
    "smogon",
    "estrategia",
    "strategy",
)


# ---------------------------------------------------------------------------
# Intent + state
# ---------------------------------------------------------------------------


class Intent(str, Enum):
    STATS = "stats"
    CALC = "calc"
    STRATEGY = "strategy"
    LORE = "lore"
    MIXED = "mixed"


_VALID_INTENTS = {i.value for i in Intent}


class GraphState(TypedDict, total=False):
    """Estado compartido entre nodos del grafo."""

    query: str
    trace_id: str
    intent: str
    entities: dict[str, Any]
    stats_response: str
    lore_response: str
    strategy_response: str
    strategy_agent_dump: dict[str, Any]
    agent_outputs: list[AgentResponse]
    verified_outputs: list[AgentResponse]
    final_response: AgentResponse


# ---------------------------------------------------------------------------
# Tool schema para classify (Haiku tool_use)
# ---------------------------------------------------------------------------


_CLASSIFY_TOOL = {
    "name": "classify_query",
    "description": (
        "Clasifica la intención del usuario y extrae entidades (Pokémon, "
        "movimientos) mencionados en la query."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": list(_VALID_INTENTS),
                "description": (
                    "stats: pregunta sobre stats/tipos/habilidades. "
                    "calc: pregunta de cálculo de daño. "
                    "lore: pregunta sobre anime/manga/regiones. "
                    "strategy: team building/coberturas/Smogon. "
                    "mixed: requiere combinar varios agentes."
                ),
            },
            "pokemon": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Nombres de Pokémon mencionados (en inglés idealmente).",
            },
            "moves": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Nombres de movimientos mencionados.",
            },
        },
        "required": ["intent"],
    },
}


_CLASSIFY_SYSTEM = (
    "Clasifica la pregunta del usuario en una de cinco intenciones y extrae "
    "los Pokémon/movimientos mencionados. Devuelve SOLO la llamada a la "
    "herramienta `classify_query`, nada de texto adicional."
)


# ---------------------------------------------------------------------------
# Heurística determinística (fallback offline o si Haiku no usa tool)
# ---------------------------------------------------------------------------


_CALC_KW = (
    "daño", "damage", "calcula", "calculate", "blizzard contra", "vs ", " vs.",
    "how much damage", "would it do",
)
_STRAT_KW = (
    "equipo", "team", "cobertura", "coverage", "tier", "smogon", "ou", "vgc",
    "competitive", "build me",
)
_LORE_KW = (
    "anime", "manga", "lore", "historia", "región", "region", "rival",
    "champion", "story",
)
_STATS_KW = (
    "stats", "tipo", "type", "types", "habilidad", "ability", "abilities",
    "movimientos", "moveset", "base stats",
)


def _heuristic_intent(query: str) -> Intent:
    q = query.lower()
    if any(kw in q for kw in _CALC_KW):
        return Intent.CALC
    if any(kw in q for kw in _STRAT_KW):
        return Intent.STRATEGY
    if any(kw in q for kw in _LORE_KW):
        return Intent.LORE
    if any(kw in q for kw in _STATS_KW):
        return Intent.STATS
    return Intent.MIXED


# Lista mínima offline para extraer nombres de Pokémon cuando no hay Haiku
# disponible. Cubre los Pokémon de las queries demo + los más populares.
# En modo online, Haiku 4.5 hace NER con el tool_use y este fallback sobra.
_OFFLINE_POKEMON_NAMES = frozenset(
    {
        "abomasnow", "alakazam", "blissey", "bulbasaur", "charizard", "charmander",
        "clefable", "corviknight", "dragapult", "dragonite", "ferrothorn", "garchomp",
        "gengar", "gholdengo", "great tusk", "greninja", "gyarados", "iron valiant",
        "jigglypuff", "kingambit", "lucario", "machamp", "mew", "mewtwo", "miraidon",
        "ogerpon", "pikachu", "rayquaza", "salamence", "scizor", "snorlax", "squirtle",
        "tinkaton", "toxapex", "tyranitar", "venusaur", "zacian", "zamazenta",
    }
)


def _heuristic_extract_pokemon(query: str) -> list[str]:
    """NER ofline: matchea nombres de Pokémon por substring case-insensitive.

    Suficientemente bueno para las queries demo. Cuando hay API key, el grafo
    pasa por ``classify_with_tools`` y este atajo ni se usa.
    """
    q = query.lower()
    found = [name for name in _OFFLINE_POKEMON_NAMES if name in q]
    # Capitalizamos antes de devolver para que stats_agent → PokéAPI funcione.
    return [name.title() for name in sorted(set(found))]


def _agents_for_intent(intent: Intent) -> list[str]:
    """Qué nodos lanzar según la intent."""
    if intent == Intent.STATS:
        return ["stats_agent"]
    if intent == Intent.CALC:
        return ["calculator_agent", "stats_agent"]  # stats da contexto del defensor
    if intent == Intent.LORE:
        return ["lore_agent"]
    if intent == Intent.STRATEGY:
        return ["strategy_agent", "stats_agent"]
    # MIXED
    return ["stats_agent", "lore_agent", "strategy_agent"]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class Orchestrator:
    """Orquestador que clasifica queries y enruta a agentes especializados.

    Usa Groq (Llama 3.3 70B) para clasificación rápida y evita saturar Ollama.
    Mantiene la firma pública anterior (``handle``) para no romper la API y
    añade ``handle_stream`` para SSE.
    """

    def __init__(
        self,
        *,
        llm: LLMClient | None = None,
        pokeapi_client: PokeAPIClient | None = None,
        stats_agent: StatsAgent | None = None,
        calculator_agent: CalculatorAgent | None = None,
        lore_agent: LoreAgent | None = None,
        strategy_agent: StrategyAgent | None = None,
        verifier: VerifierAgent | None = None,
        synthesizer: Synthesizer | None = None,
    ) -> None:
        self._llm = llm or get_llm_client()
        self._pokeapi = pokeapi_client or get_client()
        self.stats_agent = stats_agent or StatsAgent()
        self.calculator_agent = calculator_agent or CalculatorAgent()
        self.lore_agent = lore_agent or LoreAgent(llm=self._llm)
        self.strategy_agent = strategy_agent or StrategyAgent(llm=self._llm)
        self.verifier = verifier or VerifierAgent()
        self.synthesizer = synthesizer or Synthesizer(llm=self._llm)
        self._graph = self._build_graph()

    # ------------------------------------------------------------------
    # Graph builder
    # ------------------------------------------------------------------

    def _build_graph(self) -> Any:
        """Grafo SECUENCIAL para respetar rate limits."""
        graph = StateGraph(GraphState)
        graph.add_node("classify", self._node_classify)
        graph.add_node("stats", self._node_dispatch)
        graph.add_node("synthesize", self._node_synthesize)
        graph.add_edge(START, "classify")
        graph.add_edge("classify", "stats")
        graph.add_edge("stats", "synthesize")
        graph.add_edge("synthesize", END)
        return graph.compile()

    # ------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------

    def _node_classify(self, state: GraphState) -> GraphState:
        """Clasificación por regex, sin LLM."""
        print(f"\n>>> NODE: classify | Query: {state.get('query', '')}")
        raw = state["query"]
        query = raw.lower()
        strategy_patterns = (
            "recomienda",
            "compañeros",
            "teammates",
            " ou ",
            " ou?",
            " en ou",
            "build me",
            "armar equipo",
            "team building",
        )
        if any(kw in query for kw in _STRATEGY_KEYWORDS) or any(p in query for p in strategy_patterns):
            intent = "strategy"
        elif any(word in query for word in ["tipo", "types", "cuáles", "de qué tipo", "type"]):
            intent = "stats"
        elif any(word in query for word in ["daño", "damage", "blizzard", "calcul", "ataque"]):
            intent = "calculation"
        elif any(word in query for word in ["historia", "lore", "describe", "qué es", "pokédex"]):
            intent = "lore"
        else:
            intent = "stats"
        extracted = self._extract_pokemon_name(raw)
        merged: dict[str, Any] = dict(state.get("entities") or {})
        merged.update(extracted)
        print(f"<<< NODE: classify | Intent: {intent}")
        return {"intent": intent, "entities": merged}

    def _extract_pokemon_name(self, query: str) -> dict[str, Any]:
        """Extrae nombre Pokémon sin LLM."""
        query_norm = query.lower().replace("’", "'")
        query_norm = re.sub(r"(\w+)'s\b", r"\1", query_norm)
        # Coincidencia por lista (ordenar por longitud para preferir nombres largos).
        for name in sorted(COMMON_POKEMON, key=len, reverse=True):
            if name in query_norm:
                return {"pokemon": name}
        words = re.findall(r"[A-Za-z][A-Za-z'\-]*", query)
        for word in reversed(words):
            clean = word.strip("?¿.,;:'").lower()
            if len(clean) <= 3 or clean in _EXTRACT_STOPWORDS:
                continue
            if clean in ["tipo", "tipos", "cuáles", "son", "tiene", "cuál"]:
                continue
            return {"pokemon": clean}
        return {"pokemon": "pikachu"}

    def _node_dispatch(self, state: GraphState) -> GraphState:
        """Dispatch multipropósito: strategy, cálculo y respuestas ricas."""
        intent = state.get("intent", "stats")
        print(f"\n>>> NODE: dispatch | Intent: {intent}")
        entities = state.get("entities") or {}
        pokemon_name = entities.get("pokemon")
        tid = TraceId(str(state.get("trace_id") or uuid4().hex[:12]))

        if intent == "strategy":
            poke = entities.get("pokemon")
            ctx: dict[str, Any] = {}
            if poke:
                ctx["pokemon_hint"] = str(poke)
            agent_input = AgentInput(query=state["query"], trace_id=tid, context=ctx)
            strat_resp = self.strategy_agent.run(agent_input)
            state = dict(state)
            state["strategy_agent_dump"] = strat_resp.model_dump(mode="json")
            state["stats_response"] = json.dumps({"skipped": True, "reason": "strategy"})
            print("<<< NODE: dispatch | Agent outputs: strategy_agent_dump=1")
            return state

        if intent == "calculation":
            print("<<< NODE: dispatch | Agent outputs: calculator_path")
            return self.calculator_agent.execute(state)  # type: ignore[return-value]

        out = dict(state)
        try:
            out = self.stats_agent.execute(out)  # type: ignore[assignment]
        except Exception as exc:
            log.error("orchestrator.stats_failed", error=str(exc))

        if pokemon_name:
            try:
                out = self.lore_agent.execute(out)  # type: ignore[assignment]
            except Exception as exc:
                log.error("orchestrator.lore_failed", error=str(exc))

        if pokemon_name and intent == "lore":
            try:
                out = self.strategy_agent.execute(out)  # type: ignore[assignment]
            except Exception as exc:
                log.error("orchestrator.strategy_info_failed", error=str(exc))

        count = 0
        if out.get("stats_response"):
            count += 1
        if out.get("lore_response"):
            count += 1
        if out.get("strategy_response") or out.get("strategy_agent_dump"):
            count += 1
        print(f"<<< NODE: dispatch | Agent outputs: {count}")
        return out

    def _node_verify(self, state: GraphState) -> GraphState:
        outputs = state.get("agent_outputs", []) or []
        return {"verified_outputs": outputs}

    def _node_synthesize(self, state: GraphState) -> GraphState:
        print(f"\n>>> NODE: synthesize | Intent: {state.get('intent', 'N/A')}")
        print(f"    Stats present: {'stats_response' in state}")
        print(f"    Lore present: {'lore_response' in state}")
        print(f"    Strategy present: {'strategy_agent_dump' in state}")
        sd = dict(state)
        if "strategy_agent_dump" in sd and sd["strategy_agent_dump"]:
            print("DEBUG: _node_synthesize path STRATEGY")
            strat = AgentResponse.model_validate(sd["strategy_agent_dump"])
            text = self.synthesizer._format_strategy(sd).strip() or strat.content
            final = AgentResponse(
                agent="synthesizer",
                content=text,
                confidence=float(strat.confidence),
                trace_id=TraceId(sd["trace_id"]),
                sources=strat.sources,
                data={**strat.data, "intent": "strategy", "fast_path": False},
            )
            print(f"<<< NODE: synthesize | Response length: {len(text)}")
            return {"final_response": final}

        print("DEBUG: Llamando a synthesizer.synthesize()")
        synth_state = self.synthesizer.synthesize(sd)
        text = str(synth_state.get("final_response", "Error generando respuesta."))
        sources: list[Source] = []
        try:
            payload = json.loads(sd.get("stats_response", "{}"))
            slug = str(payload.get("name", "pikachu")).lower()
            if "error" not in payload and slug and not payload.get("skipped"):
                sources.append(
                    Source(
                        id=f"pokeapi:{slug}",
                        title=f"PokéAPI · {slug}",
                        url=f"https://pokeapi.co/api/v2/pokemon/{slug}",
                        kind="pokeapi",
                    )
                )
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
        final = AgentResponse(
            agent="synthesizer",
            content=text,
            confidence=0.9,
            trace_id=TraceId(sd["trace_id"]),
            sources=sources,
            data={"intent": sd.get("intent", "stats"), "fast_path": True},
        )
        print(f"<<< NODE: synthesize | Response length: {len(text)}")
        return {"final_response": final}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_agent_context(
        agent_name: str,
        entities: dict[str, Any],
        names: list[str],
    ) -> dict[str, Any]:
        """Inyecta hints específicas de cada agente (e.g., pokemon_name)."""
        ctx: dict[str, Any] = {"entities": entities}
        if agent_name == "stats_agent" and names:
            ctx["pokemon_name"] = names[0]
        if agent_name == "calculator_agent" and "calculator_request" in entities:
            ctx["calculator_request"] = entities["calculator_request"]
        return ctx

    @staticmethod
    def _calculator_skipped(ai: AgentInput) -> AgentResponse:
        return AgentResponse(
            agent="calculator_agent",
            content=(
                "Para calcular daño necesito attacker/defender/move tipados. "
                "La API debería empaquetar un `CalculatorRequest` en el contexto "
                "antes de invocar el orchestrator."
            ),
            confidence=0.0,
            trace_id=ai.trace_id,
            data={"skipped": True, "entities": ai.context.get("entities", {})},
        )

    def _try_build_calc_request(
        self,
        query: str,
        entities: dict[str, Any],
    ) -> tuple[CalculatorRequest | None, dict[str, Any]]:
        extracted: dict[str, Any] = {}
        names_raw = entities.get("pokemon", [])
        names = [str(n) for n in names_raw] if isinstance(names_raw, list) else []
        q = query.strip()

        nature_match = re.search(r"\b([A-Za-z]+)\s+natured\s+([A-Za-z'\-]+)", q, re.I)
        if nature_match:
            extracted["attacker_nature"] = nature_match.group(1).title()
            extracted["attacker"] = nature_match.group(2).strip().title()

        move_match = re.search(r"\buses?\s+([A-Za-z'\- ]+?)\s+against\b", q, re.I)
        if move_match:
            extracted["move"] = move_match.group(1).strip().title()

        def_match = re.search(r"\bagainst\s+(?:a|an|the|my)?\s*([A-Za-z'\- ]+?)(?:\s+with|\?|,|$)", q, re.I)
        if def_match:
            extracted["defender"] = def_match.group(1).strip().title()

        ev_match = re.search(r"(\d+)\s*sp\.?\s*d\s*evs?", q, re.I)
        if ev_match:
            extracted["defender_spd_evs"] = int(ev_match.group(1))

        if "attacker" not in extracted and names:
            extracted["attacker"] = names[0]
        if "defender" not in extracted and len(names) > 1:
            extracted["defender"] = names[1]

        moves_raw = entities.get("moves", [])
        if "move" not in extracted and isinstance(moves_raw, list) and moves_raw:
            extracted["move"] = str(moves_raw[0]).title()

        required = {"attacker", "defender", "move"}
        if not required <= set(extracted):
            return None, extracted

        nature_name = str(extracted.get("attacker_nature", "Hardy")).upper()
        nature = Nature.__members__.get(nature_name, Nature.HARDY)
        def_spd_evs = int(extracted.get("defender_spd_evs", 0))
        defender_evs = EVs(special_defense=def_spd_evs)

        try:
            attacker = self._pokeapi.to_domain_pokemon(
                str(extracted["attacker"]),
                nature=nature,
            )
            defender = self._pokeapi.to_domain_pokemon(
                str(extracted["defender"]),
                evs=defender_evs,
            )
            move = self._pokeapi.to_domain_move(str(extracted["move"]))
            return (
                CalculatorRequest(attacker=attacker, defender=defender, move=move),
                extracted,
            )
        except Exception as exc:
            extracted["parse_error"] = str(exc)
            return None, extracted

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def handle(
        self,
        query: str,
        *,
        trace_id: TraceId | None = None,
        context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """Ejecuta el grafo end-to-end y devuelve la respuesta final.

        ``context`` opcional permite a la API empaquetar un ``calculator_request``
        cuando la query es de cálculo (vendrá del FormUI del damage calc).
        """
        tid = str(trace_id) if trace_id else uuid4().hex[:12]
        initial: GraphState = {
            "query": query,
            "trace_id": tid,
            "agent_outputs": [],
            "verified_outputs": [],
        }
        if context and "calculator_request" in context:
            # El node_dispatch necesita ver esto; lo empaquetamos en entities
            # para que llegue a CalculatorAgent.
            initial["entities"] = {"calculator_request": context["calculator_request"]}

        try:
            final_state: GraphState = self._graph.invoke(initial)  # type: ignore[arg-type]
        except Exception as exc:
            raise AgentError(
                "Fallo ejecutando el grafo del orchestrator",
                details={"error": str(exc)},
            ) from exc

        response = final_state.get("final_response")
        if not isinstance(response, AgentResponse):
            raise AgentError(
                "El grafo no produjo `final_response`",
                details={"state_keys": list(final_state.keys())},
            )
        return response

    def handle_stream(
        self,
        query: str,
        *,
        trace_id: TraceId | None = None,
        context: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Versión streaming. Yieldea eventos serializables tipo SSE.

        Eventos emitidos (cada uno es un dict listo para ``json.dumps``):
        - ``{"event": "intent",  "data": {...}}``
        - ``{"event": "agent",   "data": {agent, confidence}}`` por cada output
        - ``{"event": "token",   "data": "<chunk>"}`` durante synthesize
        - ``{"event": "done",    "data": {sources, confidence_level, ...}}``
        """
        tid = str(trace_id) if trace_id else uuid4().hex[:12]

        # 1) Classify + dispatch + verify (sin streaming): usamos el graph hasta verify.
        partial_state: GraphState = {
            "query": query,
            "trace_id": tid,
            "agent_outputs": [],
            "verified_outputs": [],
        }
        if context and "calculator_request" in context:
            partial_state["entities"] = {"calculator_request": context["calculator_request"]}
        partial_state.update(self._node_classify(partial_state))  # type: ignore[arg-type]
        yield {
            "event": "intent",
            "data": json.dumps(
                {
                    "intent": partial_state.get("intent"),
                    "entities": partial_state.get("entities", {}),
                }
            ),
        }

        partial_state.update(self._node_dispatch(partial_state))  # type: ignore[arg-type]

        synth_work = dict(partial_state)
        if partial_state.get("strategy_agent_dump"):
            strat = AgentResponse.model_validate(partial_state["strategy_agent_dump"])
            fast_text = self.synthesizer._format_strategy(dict(partial_state)).strip() or strat.content
            fast_sources = list(strat.sources)
        else:
            self.synthesizer.synthesize(synth_work)
            fast_text = str(synth_work.get("final_response", ""))
            fast_sources = []
            try:
                payload = json.loads(partial_state.get("stats_response", "{}"))
                slug = str(payload.get("name", "")).lower()
                if slug and "error" not in payload:
                    fast_sources.append(
                        Source(
                            id=f"pokeapi:{slug}",
                            title=f"PokéAPI · {slug}",
                            url=f"https://pokeapi.co/api/v2/pokemon/{slug}",
                            kind="pokeapi",
                        )
                    )
            except (json.JSONDecodeError, TypeError, KeyError):
                pass

        _agent_evt = (
            "strategy_agent" if partial_state.get("strategy_agent_dump") else "stats_agent"
        )
        _conf_evt = (
            float(AgentResponse.model_validate(partial_state["strategy_agent_dump"]).confidence)
            if partial_state.get("strategy_agent_dump")
            else 0.95
        )
        yield {
            "event": "agent",
            "data": json.dumps(
                {
                    "agent": _agent_evt,
                    "confidence": _conf_evt,
                    "sources": [s.model_dump(mode="json") for s in fast_sources],
                }
            ),
        }

        chunk_size = 32
        for i in range(0, len(fast_text), chunk_size):
            yield {"event": "token", "data": fast_text[i : i + chunk_size]}

        final = AgentResponse(
            agent="synthesizer",
            content=fast_text,
            confidence=0.9,
            trace_id=TraceId(tid),
            sources=fast_sources,
            data={"intent": partial_state.get("intent", "stats"), "fast_path": True},
        )
        yield {
            "event": "done",
            "data": json.dumps(
                {
                    "trace_id": tid,
                    "confidence": final.confidence,
                    "confidence_level": final.confidence_level.value,
                    "sources": [s.model_dump(mode="json") for s in final.sources],
                    "data": final.data,
                }
            ),
        }


__all__ = ["GraphState", "Intent", "Orchestrator"]
