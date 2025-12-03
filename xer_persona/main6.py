import json
import operator
import os
from datetime import datetime
from typing import Any, Optional, TypedDict

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore
from typing_extensions import Annotated, TypedDict

load_dotenv()


# ========== Configurar Memória ==========

checkpointer = MemorySaver()
store = InMemoryStore()

# ========== ESTADO COMPARTILHADO ==========


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    current_agent: str  # "profile" ou "recommendation"
    next_node: str  # Rastreamento de fluxo


# ========== DEFINIR NAMESPACES DO STORE ==========

USER_DATA_STRUCTURE = {
    "profile": {
        "personal": ["name", "age", "gender", "email", "phone"],
        "demographics": ["nationality", "date_of_birth"],
        "education": [
            "education_level",
            "university",
            "field_of_study",
            "graduation_year",
        ],
        "family": ["marital_status", "number_of_children", "has_pets", "pet_types"],
        "professional": ["job_title", "company", "industry", "years_of_experience"],
        "location": ["country", "state", "city", "timezone"],
        "preferences": ["language", "currency"],
    },
    "interests": {
        "technology": ["programming_languages", "frameworks", "specializations"],
        "hobbies": ["sports", "arts", "music_genres"],
        "reading": ["book_genres", "favorite_authors"],
        "food": ["cuisines", "dietary_restrictions"],
        "travel": ["favorite_destinations", "travel_style", "budget_travel_preference"],
    },
    "history": {
        "travels": [
            "destination",
            "country",
            "year_visited",
            "duration_days",
            "rating",
        ],
        "books_read": ["title", "author", "rating", "date_read"],
        "movies_watched": ["title", "director", "rating", "date_watched"],
        "places_visited": ["place_name", "city", "country", "rating"],
    },
}

# ========== FERRAMENTAS PARA GERENCIAR PERFIL ==========


@tool
def add_interest(category: str, interest: str, confidence: float) -> str:
    """Adiciona um interesse ao perfil do usuário."""
    namespace = ("user_profile", "interests")
    interest_id = f"{category}_{interest.lower().replace(' ', '_')}"

    interest_data = {
        "id": interest_id,
        "category": category,
        "interest": interest,
        "confidence": confidence,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }

    store.put(namespace, interest_id, json.dumps(interest_data))
    return f"✓ Interesse '{interest}' adicionado na categoria '{category}'"


@tool
def refine_interest_confidence(
    category: str, interest: str, new_confidence: float
) -> str:
    """Refina a confiança de um interesse existente."""
    namespace = ("user_profile", "interests")
    interest_id = f"{category}_{interest.lower().replace(' ', '_')}"

    existing = store.get(namespace, interest_id)
    if not existing:
        return f"✗ Interesse '{interest}' não encontrado"

    interest_data = json.loads(existing.value)
    interest_data["confidence"] = max(0.0, min(1.0, new_confidence))
    store.put(namespace, interest_id, json.dumps(interest_data))
    return f"✓ Confiança de '{interest}' atualizada para {int(new_confidence * 100)}%"


@tool
def mark_item_consumed(category: str, item_name: str, rating: float = 0.0) -> str:
    """Marca um item como consumido (ex: livro lido, filme assistido)."""
    namespace = ("user_profile", "consumed")
    item_id = f"{category}_{item_name.lower().replace(' ', '_')}"

    consumed_data = {
        "id": item_id,
        "category": category,
        "item_name": item_name,
        "rating": rating,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }

    store.put(namespace, item_id, json.dumps(consumed_data))
    return f"✓ '{item_name}' marcado como consumido (rating: {rating}/5)"


@tool
def get_consumed_items(category: str = None) -> str:
    """Recupera itens já consumidos para evitar recomendações duplicadas."""
    namespace = ("user_profile", "consumed")
    all_consumed = store.search(namespace)

    consumed_list = []
    for item in all_consumed:
        data = json.loads(item.value)
        if category is None or data["category"] == category:
            consumed_list.append(
                {
                    "item": data["item_name"],
                    "category": data["category"],
                    "rating": data["rating"],
                }
            )

    if not consumed_list:
        return "Nenhum item consumido registrado"

    result = "📚 Itens já consumidos:\n"
    for item in consumed_list:
        result += (
            f"  - {item['item']} ({item['category']}) - Rating: {item['rating']}/5\n"
        )

    return result


@tool
def get_user_profile() -> str:
    """Recupera o perfil completo do usuário."""
    namespace = ("user_profile", "interests")
    all_interests = store.search(namespace)

    if not all_interests:
        return "Perfil vazio - nenhum interesse registrado"

    profile = {}
    for item in all_interests:
        data = json.loads(item.value)
        category = data["category"]
        if category not in profile:
            profile[category] = []
        profile[category].append(
            {"interest": data["interest"], "confidence": data["confidence"]}
        )

    result = "📋 Seu Perfil de Interesses:\n"
    for category, interests in sorted(profile.items()):
        result += f"\n🏷️ {category.upper()}:\n"
        for item in sorted(interests, key=lambda x: x["confidence"], reverse=True):
            confidence_bar = "█" * int(item["confidence"] * 10) + "░" * (
                10 - int(item["confidence"] * 10)
            )
            result += f"  - {item['interest']} [{confidence_bar}] {int(item['confidence'] * 100)}%\n"

    return result


@tool
def save_user_data(
    category: str,
    subcategory: str,
    data_key: str,
    data_value: Any,
    runtime: ToolRuntime,
) -> str:
    """
    Ferramenta genérica para salvar QUALQUER dado do usuário.

    Exemplos:
    - save_user_data("profile", "personal", "name", "Alice")
    - save_user_data("interests", "technology", "programming_languages", ["Python", "JavaScript"])
    - save_user_data("history", "travels", "destination", "Rio de Janeiro")
    """
    user_id = runtime.state.get("user_id", "default_user")
    namespace = (user_id, category, subcategory)

    # Validar que o caminho existe no mapeamento
    if category not in USER_DATA_STRUCTURE:
        return f"❌ Categoria '{category}' não existe no mapeamento"

    if subcategory not in USER_DATA_STRUCTURE[category]:
        print(f"❌ Subcategoria '{subcategory}' não cadastrada em '{category}'")
        USER_DATA_STRUCTURE[category].append(subcategory)

    if data_key not in USER_DATA_STRUCTURE[category][subcategory]:
        print(f"⚠️ Aviso: '{data_key}' pode não ser um campo esperado")
        USER_DATA_STRUCTURE[category][subcategory].append(data_key)

    # Salvar dados
    data_entry = {
        "key": data_key,
        "value": data_value,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "category": category,
        "subcategory": subcategory,
    }

    key = f"{data_key}_{str(data_value)[:10].lower().replace(' ', '_')}"
    runtime.store.put(namespace, key, json.dumps(data_entry))

    return f"✓ {category}/{subcategory}: {data_key} = {data_value}"


@tool
def get_user_data(
    category: str, subcategory: str = None, runtime: ToolRuntime = None
) -> str:
    """
    Ferramenta genérica para recuperar dados do usuário.

    Exemplos:
    - get_user_data("profile", "personal")  # Todos dados pessoais
    - get_user_data("interests", "technology")  # Interesses em tech
    - get_user_data("history")  # Todos históricos
    """
    user_id = runtime.state.get("user_id", "default_user")

    if category not in USER_DATA_STRUCTURE:
        return f"❌ Categoria '{category}' não existe"

    if subcategory:
        if subcategory not in USER_DATA_STRUCTURE[category]:
            return f"❌ Subcategoria '{subcategory}' não existe em '{category}'"
        namespace = (user_id, category, subcategory)
    else:
        # Retornar todas as subcategorias
        namespace = (user_id, category)

    items = runtime.store.search(namespace)

    if not items:
        return f"Nenhum dado encontrado em {category}/{subcategory or 'todas'}"

    result = f"📋 Dados de {category}/{subcategory or 'todas as subcategorias'}:\n"
    for item in items:
        data = json.loads(item.value)
        result += f"  - {data['key']}: {data['value']}\n"

    return result


@tool
def list_all_user_data(runtime: ToolRuntime) -> str:
    """Mostra TODOS os dados salvos do usuário (resumo)"""
    user_id = runtime.state.get("user_id", "default_user")

    result = f"📊 Resumo do Perfil Completo de {user_id}:\n\n"

    for category, subcategories in USER_DATA_STRUCTURE.items():
        result += f"🏷️ {category.upper()}:\n"
        for subcategory in subcategories:
            namespace = (user_id, category, subcategory)
            items = runtime.store.search(namespace)
            count = len(items)
            result += f"  • {subcategory}: {count} registros\n"
        result += "\n"

    return result


# ========== AGENTES ESPECIALIZADOS (nós) ==========
def profile_agent_node(state: AgentState):
    """Nó: Gerencia perfil do usuário"""
    model = ChatOpenAI(model="gpt-4o-mini")

    # Mesmo setup anterior
    tools = [add_interest, refine_interest_confidence, get_user_profile]

    # Executar o agente especializado
    profile_agent = create_agent(
        model=model,
        tools=tools,
        system_prompt="""Você é especialista em gerenciar perfis...""",
    )

    result = profile_agent.invoke({"messages": state["messages"]})

    return {
        "messages": [result["messages"][-1]],  # Adiciona resposta ao histórico
        "current_agent": "profile",
    }


def recommendation_agent_node(state: AgentState):
    """Nó: Gera recomendações personalizadas"""
    model = ChatOpenAI(model="gpt-4o-mini")
    tools = [get_user_profile, get_consumed_items, mark_item_consumed]

    recommendation_agent = create_agent(
        model=model,
        tools=tools,
        system_prompt="""Você é especialista em recomendações...""",
    )

    result = recommendation_agent.invoke({"messages": state["messages"]})

    return {
        "messages": [result["messages"][-1]],
        "current_agent": "recommendation",
    }


# ========== SUPERVISOR (roteador inteligente) ==========
def supervisor_node(state: AgentState):
    """Nó: Decide para qual agente rotear"""
    model = ChatOpenAI(model="gpt-4o-mini")

    # Prompt que retorna QUAL agente deve ser chamado
    system_prompt = """Você é um supervisor que roteia tarefas para especialistas.

Baseado na mensagem do usuário, decida:
- Se é sobre ADICIONAR/VER PERFIL → rotear para "profile_agent"
- Se é sobre RECOMENDAÇÕES → rotear para "recommendation_agent"

Responda APENAS com o nome do agente: "profile_agent" ou "recommendation_agent"
"""

    last_message = state["messages"][-1].content

    decision = model.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Decisão: {last_message}"},
        ]
    )

    agent_choice = decision.content.strip().lower()

    if "recommendation" in agent_choice:
        return {"next_node": "recommendation_agent", "messages": []}
    elif "profile" in agent_choice:
        return {"next_node": "profile_agent", "messages": []}
    else:
        # Default
        return {"next_node": "profile_agent", "messages": []}


# ========== ROTEAMENTO CONDICIONAL ==========
def route_to_agent(state: AgentState):
    """Função de roteamento condicional"""
    return state.get("next_node", "profile_agent")


# ========== CONSTRUIR GRAFO ==========
graph_builder = StateGraph(AgentState)

# Adicionar nós
graph_builder.add_node("supervisor", supervisor_node)
graph_builder.add_node("profile_agent", profile_agent_node)
graph_builder.add_node("recommendation_agent", recommendation_agent_node)

# Conectar fluxo
graph_builder.add_edge(START, "supervisor")  # Sempre começa no supervisor
graph_builder.add_conditional_edges(
    "supervisor",
    route_to_agent,  # Função que decide o próximo nó
    {
        "profile_agent": "profile_agent",
        "recommendation_agent": "recommendation_agent",
    },
)
graph_builder.add_edge("profile_agent", END)
graph_builder.add_edge("recommendation_agent", END)

# ========== COMPILAR E USAR ==========

graph = graph_builder.compile(
    checkpointer=MemorySaver()  # Persistência automática
)

# TESTE
if __name__ == "__main__":
    config = {"configurable": {"thread_id": "alice_thread"}}

    # Entrada 1: Adicionar interesse
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="Sou Gustavo, um sociólogo que trabalha com data science.Gosto muito de Python, Machine Learning e RPG. Também sou fã de ficção científica. Adorei Ghost in the shell."
                )
            ],
            "next_node": "",
        },
        config,
    )
    print(f"Resultado: {result['messages'][-1].content}")

    # Entrada 2: Pedir recomendações
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content="Me recomenda algumas coisas interessantes")
            ],
            "next_node": "",
        },
        config,
    )
    print(f"Resultado: {result['messages'][-1].content}")

    # Entrada 3: Descrever perfil
    result = graph.invoke(
        {
            "messages": [HumanMessage(content="Me descreva meu perfil")],
            "next_node": "",
        },
        config,
    )
    print(f"Resultado: {result['messages'][-1].content}")
