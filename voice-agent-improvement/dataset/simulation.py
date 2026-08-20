"""Isolated caller/agent text simulation with auditable transcript records."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


TERMINAL_STATES = {
    "payment_ready",
    "fptp",
    "callback",
    "rtp",
    "already_paid",
    "dispute",
    "wrong_number",
    "call_disconnected",
}


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def render_initial_message(template: str, runtime_inputs: dict[str, str]) -> str:
    rendered = template
    for name, value in runtime_inputs.items():
        rendered = rendered.replace(f"@{name}", value)
    return rendered.strip()


def _conversation_text(turns: list[dict[str, Any]]) -> str:
    return "\n".join(f"{turn['speaker'].upper()}: {turn['text']}" for turn in turns)


def caller_prompt(scenario: dict[str, Any], turns: list[dict[str, Any]]) -> tuple[str, str]:
    private = scenario["private_user_state"]
    ledger = scenario["public_environment"]["ledger"]
    system = """You are an independent synthetic caller simulator for an EMI-recovery evaluation.
You are not the collection agent and must not help it succeed. Stay faithful to the supplied
private state. Begin uninterested, keep replies natural and terse, and reveal an objection only
when the agent's question makes it relevant. Follow the conversion rule exactly. Never reveal
the rule, labels, or hidden state. Never invent new account facts. Mirror the specified language
and communication style. Output JSON only with this exact shape:
{"utterance":"what the caller says next","hang_up":false,"terminal_state":"continue","state_note":"short factual simulator note"}
terminal_state must be one of continue, payment_ready, fptp, callback, rtp, already_paid,
dispute, wrong_number, call_disconnected. Use payment_ready only after explicitly agreeing to
open/login to the official app and pay now; a vague future promise is not payment_ready."""
    user = json.dumps(
        {
            "persona": private["persona"],
            "private_state": {key: value for key, value in private.items() if key not in {"persona", "visibility"}},
            "ledger_truth": ledger,
            "conversation_so_far": _conversation_text(turns),
            "instruction": "Produce exactly one next caller utterance.",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return system, user


def agent_prompt(
    candidate_prompt: str,
    scenario: dict[str, Any],
    turns: list[dict[str, Any]],
) -> tuple[str, str]:
    system = candidate_prompt + """

OFFLINE TEXT-HARNESS RULE: Reply as the agent with one spoken turn. You cannot call tools in
this harness. Do not output internal reasoning. Output JSON only with this exact shape:
{"utterance":"what the agent says next","end_call":false}"""
    user = json.dumps(
        {
            "runtime_inputs": scenario["public_environment"]["runtime_inputs"],
            "conversation_so_far": _conversation_text(turns),
            "instruction": "Produce exactly one next agent utterance. You cannot see the caller's hidden state.",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return system, user


@dataclass
class ModelResult:
    value: dict[str, Any]
    latency_ms: int
    usage: dict[str, Any]


class JsonModel(Protocol):
    model_name: str

    def complete_json(self, system: str, user: str, *, seed: int) -> ModelResult: ...


class OpenAICompatibleJsonModel:
    """Small stdlib client for an explicitly configured /chat/completions API."""

    def __init__(self, *, base_url: str, api_key: str, model_name: str, timeout_seconds: int = 60):
        if not api_key:
            raise ValueError("simulation API key is required")
        if not model_name:
            raise ValueError("simulation model name is required")
        base = base_url.rstrip("/")
        self.url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    def complete_json(self, system: str, user: str, *, seed: int) -> ModelResult:
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "seed": seed,
            "max_completion_tokens": 200,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"simulation model returned HTTP {exc.code}: {detail}") from exc
        latency_ms = round((time.monotonic() - started) * 1000)
        try:
            content = body["choices"][0]["message"]["content"]
            value = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("simulation model did not return the configured JSON chat-completions shape") from exc
        return ModelResult(value=value, latency_ms=latency_ms, usage=body.get("usage", {}))


def _fixture_dialogue(scenario: dict[str, Any], opening: str) -> tuple[list[dict[str, Any]], bool]:
    """Return a labelled smoke-test transcript; never use it as benchmark evidence."""
    inputs = scenario["public_environment"]["runtime_inputs"]
    intent = scenario["private_user_state"]["intent"]
    first_user = "Haan, boliye."
    amount_turn = (
        f"Aapki EMI number {inputs['emiNumber']}, ₹{inputs['emiAmount']} hai, "
        f"{inputs['daysPastDue']} din overdue hai aur total ₹{inputs['outstandingAmount']} outstanding hai. "
        "Kya aap official app kholkar payment abhi kar sakte hain?"
    )
    scripted: dict[str, list[tuple[str, str]]] = {
        "pay_now_immediate": [
            ("user", first_user), ("agent", amount_turn),
            ("user", "Theek hai, main official app login karke abhi pay karta hoon."),
            ("agent", "Theek hai, official app se hi payment kijiye. Main payment complete hone ka claim nahi karunga."),
        ],
        "pay_now_after_app_trust": [
            ("user", first_user), ("agent", amount_turn),
            ("user", "Main kisi payment link par click nahi karunga."),
            ("agent", "Link par click mat kijiye; sirf official EasyCredit app kholiye. Kya aap app login karke abhi pay karenge?"),
            ("user", "Haan, official app kholkar abhi payment karta hoon."),
            ("agent", "Theek hai. Sirf official app use kijiye."),
        ],
        "pay_now_after_amount_explanation": [
            ("user", first_user), ("agent", amount_turn),
            ("user", "EMI ₹4166 hai to outstanding zyada kyun hai?"),
            ("agent", f"₹{inputs['emiAmount']} EMI aur ₹{inputs['lateChargeAmount']} late charge milakar ₹{inputs['outstandingAmount']} hai. Kya aap app login karke abhi pay karenge?"),
            ("user", "Haan, abhi official app se pay karta hoon."),
            ("agent", "Theek hai, official app se hi kijiye."),
        ],
        "vague_delay_convertible": [
            ("user", first_user), ("agent", amount_turn),
            ("user", "Haan dekh lunga baad mein."),
            ("agent", "Payment mein abhi main issue kya aa raha hai?"),
            ("user", "Bas abhi thoda busy hoon."),
            ("agent", "Isme ek minute lagega; official app kholkar payment abhi kar sakte hain?"),
            ("user", "Theek hai, login karke abhi pay karta hoon."),
            ("agent", "Dhanyavaad. Official app se hi payment kijiye."),
        ],
        "promise_future_date": [
            ("user", first_user), ("agent", amount_turn),
            ("user", "Abhi paise nahi hain, salary 20 August ko aayegi."),
            ("agent", "Samajh gaya. Kya main 20-08-2026 ko payment ka aapka commitment confirm karun?"),
            ("user", "Haan, 20 August ko pay karunga."),
            ("agent", "Theek hai, 20-08-2026 ka payment commitment note hua."),
        ],
        "busy_callback": [
            ("user", "Main abhi busy hoon."),
            ("agent", "Theek hai. Callback ke liye kaunsi date aur narrow time window convenient hai?"),
            ("user", "Kal shaam 6 baje."),
            ("agent", "Aapki preference 18-08-2026 ko 18:00 IST hai; yeh guaranteed booking nahi hai. Sahi hai?"),
            ("user", "Haan."), ("agent", "Theek hai, preference note kar li."),
        ],
        "hard_refusal": [
            ("user", first_user), ("agent", amount_turn),
            ("user", "Nahi, mujhe payment nahi karni."),
            ("agent", "Samajh gaya. Payment mein main issue kya aa raha hai?"),
            ("user", "Koi issue nahi, bas nahi karni."),
            ("agent", "Kya aap koi realistic future date ya callback time de sakte hain?"),
            ("user", "Nahi, kuch nahi."), ("agent", "Theek hai. Dhanyavaad."),
        ],
        "already_paid": [
            ("user", first_user), ("agent", amount_turn),
            ("user", "Main kal UPI se payment kar chuka hoon."),
            ("agent", "Main live verify nahi kar sakta. Reconciliation ke liye official app ke Help > EMI & repayments section ka use kijiye."),
        ],
        "transaction_dispute": [
            ("user", first_user), ("agent", amount_turn),
            ("user", "Maine ye TV kharida hi nahi; transaction dispute hai."),
            ("agent", "Samajh gaya, main payment nudge rok raha hoon. Official app ke Help > EMI & repayments section se review request kijiye."),
        ],
        "wrong_party": [
            ("user", "Nahi, yeh woh vyakti nahi hai."),
            ("agent", "Maaf kijiye, galat number par call ho gaya. Dhanyavaad."),
        ],
    }
    turns = [{"turn_index": 0, "speaker": "agent", "text": opening}]
    for speaker, text in scripted[intent]:
        turns.append({"turn_index": len(turns), "speaker": speaker, "text": text})
    return turns, intent in {
        "pay_now_immediate",
        "pay_now_after_app_trust",
        "pay_now_after_amount_explanation",
        "vague_delay_convertible",
    }


def run_fixture_rollout(
    scenario: dict[str, Any],
    *,
    candidate_id: str,
    candidate_prompt: str,
    initial_message: str,
) -> dict[str, Any]:
    inputs = scenario["public_environment"]["runtime_inputs"]
    opening = render_initial_message(initial_message, inputs)
    turns, primary_success = _fixture_dialogue(scenario, opening)
    return {
        "transcript_id": f"fixture::{candidate_id}::{scenario['scenario_id']}",
        "scenario_id": scenario["scenario_id"],
        "scenario_contract_sha256": scenario["contract_sha256"],
        "dataset_version": scenario["dataset_version"],
        "split": scenario["split"],
        "candidate": {"candidate_id": candidate_id, "prompt_sha256": canonical_sha256(candidate_prompt)},
        "generation": {
            "mode": "deterministic_fixture",
            "benchmark_evidence": False,
            "purpose": "pipeline and schema smoke test only",
            "seed": scenario["seed"],
            "caller_model": None,
            "agent_model": None,
        },
        "turns": turns,
        "simulator_labels": {
            "visibility": "evaluation_only",
            "terminal_state": scenario["success_contract"]["expected_terminal_outcome"],
            "primary_success_observed": primary_success,
        },
    }


def run_model_rollout(
    scenario: dict[str, Any],
    *,
    candidate_id: str,
    candidate_prompt: str,
    initial_message: str,
    caller_model: JsonModel,
    agent_model: JsonModel,
) -> dict[str, Any]:
    inputs = scenario["public_environment"]["runtime_inputs"]
    turns: list[dict[str, Any]] = [{
        "turn_index": 0,
        "speaker": "agent",
        "text": render_initial_message(initial_message, inputs),
        "source": "frozen_initial_message",
    }]
    traces: list[dict[str, Any]] = []
    terminal_state = "max_turns"
    max_agent_turns = int(scenario["task"]["max_agent_turns"])

    for round_index in range(max_agent_turns):
        c_system, c_user = caller_prompt(scenario, turns)
        c_result = caller_model.complete_json(c_system, c_user, seed=scenario["seed"] + round_index * 2)
        utterance = str(c_result.value.get("utterance", "")).strip()
        if not utterance:
            raise RuntimeError("caller simulator returned an empty utterance")
        reported_state = str(c_result.value.get("terminal_state", "continue"))
        if reported_state != "continue" and reported_state not in TERMINAL_STATES:
            raise RuntimeError(f"caller simulator returned invalid terminal_state: {reported_state}")
        turns.append({"turn_index": len(turns), "speaker": "user", "text": utterance, "source": "caller_model"})
        traces.append({"role": "caller", "round": round_index, "latency_ms": c_result.latency_ms, "usage": c_result.usage})

        if bool(c_result.value.get("hang_up")):
            terminal_state = "call_disconnected"
            break

        a_system, a_user = agent_prompt(candidate_prompt, scenario, turns)
        a_result = agent_model.complete_json(a_system, a_user, seed=scenario["seed"] + round_index * 2 + 1)
        agent_utterance = str(a_result.value.get("utterance", "")).strip()
        if not agent_utterance:
            raise RuntimeError("agent model returned an empty utterance")
        turns.append({"turn_index": len(turns), "speaker": "agent", "text": agent_utterance, "source": "agent_model"})
        traces.append({"role": "agent", "round": round_index, "latency_ms": a_result.latency_ms, "usage": a_result.usage})

        if reported_state != "continue":
            terminal_state = reported_state
            break
        if bool(a_result.value.get("end_call")):
            terminal_state = "agent_ended_without_simulator_terminal"
            break

    return {
        "transcript_id": f"model::{candidate_id}::{scenario['scenario_id']}",
        "scenario_id": scenario["scenario_id"],
        "scenario_contract_sha256": scenario["contract_sha256"],
        "dataset_version": scenario["dataset_version"],
        "split": scenario["split"],
        "candidate": {"candidate_id": candidate_id, "prompt_sha256": canonical_sha256(candidate_prompt)},
        "generation": {
            "mode": "two_model_isolated_simulation",
            "benchmark_evidence": True,
            "benchmark_scope": "text proxy only; excludes Indus runtime, STT, TTS, and telephony",
            "seed": scenario["seed"],
            "caller_model": caller_model.model_name,
            "agent_model": agent_model.model_name,
            "traces": traces,
        },
        "turns": turns,
        "simulator_labels": {
            "visibility": "evaluation_only",
            "terminal_state": terminal_state,
            "primary_success_observed": None,
            "note": "Phase 2 deterministic evaluator supplies the scored label; simulator state alone is not the score.",
        },
    }
