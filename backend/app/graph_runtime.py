# app/graph_runtime.py
from __future__ import annotations
from typing import Optional

from openai import AsyncOpenAI
from supabase import Client

from .graph import build_triage_graph

_triage_graph = None

def get_triage_graph(llm_client: AsyncOpenAI, supabase: Client):
    global _triage_graph
    if _triage_graph is None:
        _triage_graph = build_triage_graph(llm_client, supabase)
    return _triage_graph
