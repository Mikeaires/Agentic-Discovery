"""Agentic Discovery — knowledge-graph-driven interviewing engine."""

from .graph import KnowledgeGraph, GraphDelta, NodeAssertion, EdgeAssertion
from .ontology import Ontology, compute_coverage
from .engine import DiscoveryEngine, InterviewResult
from .brain import Brain, MockBrain, ClaudeBrain
from .channels import InteractionChannel, TextChannel, ScriptedChannel, VoiceChannel

__all__ = [
    "KnowledgeGraph", "GraphDelta", "NodeAssertion", "EdgeAssertion",
    "Ontology", "compute_coverage", "DiscoveryEngine", "InterviewResult",
    "Brain", "MockBrain", "ClaudeBrain",
    "InteractionChannel", "TextChannel", "ScriptedChannel", "VoiceChannel",
]
