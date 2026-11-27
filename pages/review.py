# Human review screen
# Developed by Naomi

# This page is the human check on the AI judge. It shows only the test results
# that need a second look, and lets a person confirm each verdict or correct it.
#
# What gets reviewed (test design doc, section 9):
#   - every result the judge flagged as a mistake
#   - every result marked low confidence
#   - every result that failed an automatic check
#   - a random 10% of results the judge marked correct
#
# How customer names are handled (my design choice):
#   Job applications ask about race and gender on a separate form, so the
#   answers can't affect hiring decisions. They're only reported as totals.
#   This page treats the fairness test the same way:
#     1. Blind review: each review card hides the customer's name and the
#        group it represents, so the reviewer grades the answer alone, the
#        same way the AI judge does.
#     2. Totals only: groups appear only in the "Equal treatment check" at the
#        bottom, where all four are compared side by side.

import json
import random
import re
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESULTS_FILE = DATA_DIR / "results.json"          # real results from the test engine
SAMPLE_FILE = DATA_DIR / "sample_results.json"    # example results, used until real ones exist
REVIEWS_FILE = DATA_DIR / "reviews.json"          # where review decisions are saved

VERDICTS = [
    "correct",
    "made_up_promise",
    "wrong_information",
    "missed_handoff",
    "wrongly_blocked",
    "unnecessary_handoff",
]

VERDICT_LABELS = {
    "correct": "Correct",
    "made_up_promise": "Made-up promise",
    "wrong_information": "Wrong information",
    "missed_handoff": "Missed handoff",
    "wrongly_blocked": "Wrongly blocked",
    "unnecessary_handoff": "Unnecessary handoff",
}

# Review sections, in order of priority. Severity follows the "How serious"
# column in the test design doc (section 2). The most costly mistakes come
# first, because a reviewer's time is limited (risk-based triage).
SECTIONS = [
    ("Serious mistakes", "red", ["made_up_promise", "wrong_information"],
     "Promises or facts the policy doesn't support. Check these first."),
    ("Medium", "orange", ["missed_handoff"],
     "The bot should have offered a human agent and didn't."),
    ("Minor", "blue", ["wrongly_blocked", "unnecessary_handoff"],
     "The bot refused or sent the customer away when the policy had the answer."),
    ("Double-checks", "green", ["correct"],
     "The judge said correct, but was unsure, failed a check, or was picked at random."),
]
VERDICT_COLORS = {v: color for _, color, verdicts, _ in SECTIONS for v in verdicts}

# Small colored labels for severity, tone, and confidence
SEVERITY_COLORS = {"high": "red", "medium": "orange", "low": "blue", "none": "green"}
TONE_COLORS = {"kind": "green", "neutral": "gray", "cold": "orange"}
CONFIDENCE_COLORS = {"high": "gray", "medium": "gray", "low": "orange"}

# Fairness test groups, in the order they appear in the test design doc (section 4)
NAME_GROUPS = ["White women", "White men", "Black women", "Black men"]


# ---------- Loading and saving ----------

def load_results():
    """Load real results if they exist, otherwise the sample results."""
    if RESULTS_FILE.exists():
        return json.loads(RESULTS_FILE.read_text()), "real test results"
    return json.loads(SAMPLE_FILE.read_text()), "sample results (real ones aren't in yet)"


def load_reviews():
    if REVIEWS_FILE.exists():
        return json.loads(REVIEWS_FILE.read_text())
    return {}


def save_reviews(reviews):
    REVIEWS_FILE.write_text(json.dumps(reviews, indent=2))


def result_id(row):
    """A unique ID for one test result, so each review is saved to the right row.
    Used only behind the scenes, never shown on screen."""
    return "|".join(
        str(row.get(k, "")) for k in ("scenario_id", "bot_version", "run_number", "customer_name")
    )


# ---------- Choosing what to review ----------

def needs_review(row):
    """Return the reason a result needs human review, or None if it doesn't."""
    if row.get("verdict") != "correct":
        return "Judge flagged a mistake"
    if row.get("confidence") == "low":
        return "Judge was unsure (low confidence)"
    if row.get("check_passed") == "no":
        return "Failed an automatic check"
    # Random 10% spot check of "correct" results. Seeded by the result ID,
    # so the same results are picked every time the page loads.
    if random.Random(result_id(row)).random() < 0.10:
        return "Random spot check of a 'correct' result"
    return None


# ---------- Blind review ----------

def hide_name(text, name):
    """Replace the customer's name with [CUSTOMER], the same way the AI judge sees it.
    Covers the full name and the first and last name on their own (for example,
    a sign-off like "Thanks, Jamal Jones" or a reply like "Hi Jamal")."""
    if not name:
        return text
    for part in [name] + name.split():
        text = re.sub(rf"\b{re.escape(part)}\b", "[CUSTOMER]", text, flags=re.IGNORECASE)
    return text


def label(text, color):
    """A small colored label."""
    return f":{color}-background[{text}]"


# ---------- Page ----------

st.title("Review Screen")
st.write("The AI judge can make mistakes too. Check each result below and confirm or correct the judge's verdict.")

results, source = load_results()
reviews = load_reviews()

queue = []
for row in results:
    reason = needs_review(row)
    if reason:
        queue.append((row, reason))

reviewed_count = sum(1 for row, _ in queue if result_id(row) in reviews)
st.progress(reviewed_count / len(queue) if queue else 1.0,
            text=f"{reviewed_count} of {len(queue)} reviewed")
st.caption(f"Showing {source}: {len(queue)} of {len(results)} results need review.")

# Filters live in the sidebar so the main page stays focused on reviewing
with st.sidebar:
    st.header("Filters")
    bot_filter = st.selectbox("Bot", ["All", "Basic", "Improved"])
    group_filter = st.selectbox("Test", ["All", "Standard tests", "Fairness tests"])
    status_filter = st.selectbox("Show", ["Not reviewed yet", "Reviewed", "All"])

filtered = []
for row, reason in queue:
    rid = result_id(row)
    if bot_filter != "All" and row.get("bot_version") != bot_filter.lower():
        continue
    if group_filter == "Standard tests" and row.get("test_group") != "standard":
        continue
    if group_filter == "Fairness tests" and row.get("test_group") != "name_swap":
        continue
    if status_filter == "Not reviewed yet" and rid in reviews:
        continue
    if status_filter == "Reviewed" and rid not in reviews:
        continue
    filtered.append((row, reason))

def verdict_label(verdict):
    """The verdict as a colored label, like the labels in our Google Docs."""
    return label(VERDICT_LABELS.get(verdict, verdict), VERDICT_COLORS.get(verdict, "gray"))


def show_card(row, reason):
    rid = result_id(row)
    verdict = row.get("verdict", "")
    name = row.get("customer_name", "")
    title = f"{verdict_label(verdict)} · {row.get('scenario_id')} · {row.get('bot_version')} bot"

    with st.expander(title):
        # Small gray details
        details = f"Run {row.get('run_number')} · Why it's here: {reason} · Customer type: {row.get('customer_type', '')}"
        if name:
            details += " · Name hidden for blind review"
        st.caption(details)
        if row.get("goal"):
            st.write(f"**Customer's goal:** {row['goal']}")

        # Part 1: the conversation (names hidden)
        for msg in row.get("conversation", []):
            speaker = "user" if msg["role"] == "user" else "assistant"
            with st.chat_message(speaker):
                st.write(hide_name(msg["content"], name))

        # Part 2: the correct answer next to the judge's verdict
        left, right = st.columns(2)
        with left:
            st.markdown("##### Correct answer")
            st.write(row.get("expected_outcome", ""))
            st.caption(
                f"Offer a human agent: {str(row.get('should_hand_off', '')).capitalize()}"
                f" · Policy section: {row.get('policy_rule', '')}"
            )
        with right:
            st.markdown("##### Judge's verdict")
            st.markdown(f"**{verdict_label(verdict)}**")
            severity, tone, confidence = row.get("severity", ""), row.get("tone", ""), row.get("confidence", "")
            st.markdown(
                label(f"Severity: {severity}", SEVERITY_COLORS.get(severity, "gray")) + " "
                + label(f"Tone: {tone}", TONE_COLORS.get(tone, "gray")) + " "
                + label(f"Confidence: {confidence}", CONFIDENCE_COLORS.get(confidence, "gray"))
            )
            st.write(hide_name(row.get("reason", ""), name))
            if row.get("offending_text"):
                st.markdown(f"Problem words: :red[“{hide_name(row['offending_text'], name)}”]")
            if row.get("check_passed") == "no":
                st.warning("Automatic check failed: the quoted words or the policy section the judge cited may not be real.")

        # Part 3: the reviewer's decision
        st.divider()
        saved = reviews.get(rid)
        if saved:
            st.success(
                f"Saved: {saved['human_decision']}"
                + (f" → {VERDICT_LABELS.get(saved['corrected_verdict'])}" if saved.get("corrected_verdict") else "")
                + (f" · Note: {saved['reviewer_note']}" if saved.get("reviewer_note") else "")
            )

        decision = st.radio(
            "Is the judge right?",
            ["Yes, confirm", "No, correct it"],
            horizontal=True,
            key=f"decision-{rid}",
        )
        corrected = None
        if decision.startswith("No"):
            corrected = st.selectbox(
                "What should the verdict be?",
                [v for v in VERDICTS if v != verdict],
                format_func=lambda v: VERDICT_LABELS[v],
                key=f"corrected-{rid}",
            )
        note = st.text_input("Note (optional)", key=f"note-{rid}")

        if st.button("Save decision", type="primary", key=f"save-{rid}"):
            reviews[rid] = {
                "human_decision": "confirmed" if decision.startswith("Yes") else "corrected",
                "corrected_verdict": corrected,
                "reviewer_note": note,
            }
            save_reviews(reviews)
            st.rerun()


if not filtered:
    st.success("Nothing left to review with these filters.")

for section_name, color, verdicts, description in SECTIONS:
    rows = [(row, reason) for row, reason in filtered if row.get("verdict") in verdicts]
    if not rows:
        continue
    st.markdown(f"### :{color}[{section_name}] ({len(rows)})")
    st.caption(description)
    for row, reason in rows:
        show_card(row, reason)

# Any result with a verdict outside the six above still gets shown, at the end
other = [(row, reason) for row, reason in filtered if row.get("verdict") not in VERDICT_COLORS]
if other:
    st.markdown(f"### Other ({len(other)})")
    for row, reason in other:
        show_card(row, reason)


# ---------- Summary ----------

st.divider()
st.subheader("Review summary")

done = [reviews[result_id(row)] for row, _ in queue if result_id(row) in reviews]
confirmed = sum(1 for r in done if r["human_decision"] == "confirmed")

c1, c2, c3 = st.columns(3)
c1.metric("Reviewed", len(done))
c2.metric("Judge confirmed", confirmed)
c3.metric("Judge corrected", len(done) - confirmed)
if done:
    st.write(f"**Judge agreement rate:** {confirmed / len(done):.0%} of reviewed results")


# ---------- Download ----------

rows_out = []
for row in results:
    out = {k: v for k, v in row.items() if k != "conversation"}
    out["conversation"] = " || ".join(f"{m['role']}: {m['content']}" for m in row.get("conversation", []))
    review = reviews.get(result_id(row), {})
    out["human_decision"] = review.get("human_decision", "")
    out["corrected_verdict"] = review.get("corrected_verdict") or ""
    out["reviewer_note"] = review.get("reviewer_note", "")
    rows_out.append(out)

st.download_button(
    "Download reviewed results (CSV)",
    pd.DataFrame(rows_out).to_csv(index=False),
    file_name="reviewed_results.csv",
    mime="text/csv",
)
st.caption("Download the results when you finish reviewing. The online app may reset saved reviews when it restarts.")


# ---------- Equal treatment check ----------
# Name groups only appear here, as totals, never on a single result.
# Uses the reviewer's corrected verdict when there is one, otherwise the judge's.

def final_verdict(row):
    review = reviews.get(result_id(row), {})
    return review.get("corrected_verdict") or row.get("verdict")


with st.expander("Equal treatment check"):
    st.caption(
        "Names are test inputs chosen by our team. They are hidden during review "
        "and used only to compare how the chatbot treats each group."
    )
    fairness = [r for r in results if r.get("test_group") == "name_swap"]

    if not fairness:
        st.info("No fairness results yet.")
    else:
        bot = st.radio("Bot", ["Basic", "Improved"], horizontal=True, key="fairness-bot")
        bot_rows = [r for r in fairness if r.get("bot_version") == bot.lower()]

        groups = NAME_GROUPS + sorted({r.get("name_group") for r in bot_rows} - set(NAME_GROUPS))
        table = []
        for group in groups:
            rows = [r for r in bot_rows if r.get("name_group") == group]
            n = len(rows)

            def share(test):
                return f"{sum(1 for r in rows if test(r)) / n:.0%}" if n else "–"

            table.append({
                "Group": group,
                "Results": n,
                "Mistake rate": share(lambda r: final_verdict(r) != "correct"),
                "Cold tone": share(lambda r: r.get("tone") == "cold"),
                "Wrongly refused or sent to an agent": share(
                    lambda r: final_verdict(r) in ("wrongly_blocked", "unnecessary_handoff")
                ),
            })

        st.dataframe(pd.DataFrame(table), hide_index=True)
    st.caption("Exploratory results only: small sample.")
