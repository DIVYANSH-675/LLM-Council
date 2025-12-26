#!/usr/bin/env python3
"""
LLM Council - Command Line Interface
Usage: python main.py "Your question here"
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.council import create_council
from src.core.decision import Decision, BlockedDecision


def print_header():
    """Print welcome banner"""
    print("\n" + "=" * 60)
    print("🏛️  LLM COUNCIL - Multi-Agent Decision System")
    print("=" * 60)
    print("3 Agents (STORM) → 2 Judges → MoA Synthesis → Kill Switch")
    print("-" * 60)


def print_decision(decision: Decision):
    """Print a Decision object nicely"""
    print("\n" + "=" * 60)
    print("📋 DECISION SUMMARY")
    print("=" * 60)
    
    print(f"\n🆔 Decision ID: {decision.decision_id}")
    print(f"⏱️  Processing Time: {decision.processing_time_ms}ms")
    print(f"✅ Safety Passed: {decision.safety_passed}")
    
    print("\n" + "-" * 40)
    print("🤖 AGENT RESPONSES:")
    print("-" * 40)
    for i, r in enumerate(decision.agent_responses, 1):
        text = r.response_text
        if text.startswith("[Error"):
            print(f"  {i}. {r.agent_type}: ❌ ERROR")
        else:
            preview = text[:100].replace("\n", " ")
            print(f"  {i}. {r.agent_type}: {preview}...")
    
    print("\n" + "-" * 40)
    print("⚖️  JUDGE EVALUATIONS:")
    print("-" * 40)
    for e in decision.judge_evaluations:
        agent_short = e.target_agent_id.replace("agent_", "")
        print(f"  {e.judge_type:12} → {agent_short:20}: {e.total_score:.1f}/10")
    
    print("\n" + "-" * 40)
    print("🏆 SELECTION:")
    print("-" * 40)
    print(f"  Selected: {decision.selected_response.agent_type}")
    print(f"  Confidence: {decision.confidence_score:.0%}")
    print(f"  Risk Level: {decision.risk_level.value}")
    print(f"  Refined: {'Yes' if decision.was_refined else 'No'}")
    print(f"  Retried: {'Yes' if decision.was_retried else 'No'}")
    
    if decision.identified_risks:
        print("\n⚠️  IDENTIFIED RISKS:")
        for risk in decision.identified_risks:
            print(f"  • {risk}")
    
    if decision.judge_disagreement:
        print("\n⚠️  JUDGES DISAGREED on some evaluations")
    
    print("\n" + "=" * 60)
    print("📝 FINAL RESPONSE:")
    print("=" * 60)
    final = decision.get_final_response_text()
    print(f"\n{final}\n")


def print_blocked(blocked: BlockedDecision):
    """Print a BlockedDecision object"""
    print("\n" + "=" * 60)
    print("🚫 QUERY BLOCKED")
    print("=" * 60)
    print(f"\n🆔 Decision ID: {blocked.decision_id}")
    print(f"❌ Reason: {blocked.block_reason}")
    if blocked.matched_patterns:
        print(f"📋 Matched: {blocked.matched_patterns}")
    print()


async def run_query(query: str, use_mock: bool = False, skip_synthesis: bool = False):
    """Run a query through the council"""
    print(f"\n🔍 Query: {query}")
    print("\n⏳ Processing...\n")
    
    council = create_council(use_mock=use_mock, skip_synthesis=skip_synthesis)
    result = await council.decide(query)
    
    if isinstance(result, Decision):
        print_decision(result)
    else:
        print_blocked(result)
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="LLM Council - Multi-Agent Decision System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "What is the best programming language?"
  python main.py --mock "Test query"
  python main.py --fast "Quick question"
        """
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        help="Query to process"
    )
    
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock agents (no API calls)"
    )
    
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip synthesis for faster response"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Interactive mode"
    )
    
    args = parser.parse_args()
    
    print_header()
    
    if args.interactive:
        print("\n💬 Interactive Mode (type 'quit' to exit)")
        print("-" * 40)
        
        while True:
            try:
                query = input("\n📝 Your question: ").strip()
                if query.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!\n")
                    break
                if not query:
                    continue
                
                asyncio.run(run_query(query, use_mock=args.mock, skip_synthesis=args.fast))
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!\n")
                break
    
    elif args.query:
        asyncio.run(run_query(args.query, use_mock=args.mock, skip_synthesis=args.fast))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
