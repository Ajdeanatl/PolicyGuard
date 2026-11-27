import os

from openai import OpenAI, OpenAIError
import streamlit as st

from audit import CASES, POLICY, load_reviews, run_audit, save_results, summarize

st.set_page_config(page_title="PolicyGuard")
st.title("PolicyGuard")
st.write("Compare two Northern Airlines chatbots against the same policy.")

with st.expander("Northern Airlines policy"):
    st.text(POLICY)

api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL")
live = st.checkbox("Use live model", disabled=not (api_key and model))
if not (api_key and model):
    st.caption("Set OPENAI_API_KEY and OPENAI_MODEL on the server to enable live runs.")
selected = st.multiselect(
    "Audit cases", CASES, default=CASES[:2], format_func=lambda case: case.id
)
trials = st.slider("Trials per case per bot", 1, 3, 2)

if st.button("Run Audit", disabled=not selected):
    generate = None
    if live:
        client = OpenAI(api_key=api_key, timeout=20, max_retries=0)

        def generate(instructions, message):
            try:
                response = client.responses.create(
                    model=model, instructions=instructions, input=message,
                    max_output_tokens=4000,
                )
            except OpenAIError as error:
                raise RuntimeError(f"Model request failed ({type(error).__name__}).") from error
            if response.status == "incomplete":
                details = response.incomplete_details
                raise RuntimeError(f"Model response incomplete ({details.reason if details else 'unknown'}).")
            if not response.output_text.strip():
                raise RuntimeError("Model returned no text.")
            return response.output_text

    progress = st.progress(0)
    total = len(selected) * trials * 2
    st.session_state["audit_rows"] = run_audit(
        selected, trials, generate, lambda completed: progress.progress(completed / total)
    )
    st.session_state["audit_live"] = live
    if live:
        try:
            save_results(st.session_state["audit_rows"])
        except OSError:
            st.warning("Could not save results to data/results.json. Review can still open this session's run.")

rows = st.session_state.get("audit_rows", [])
if rows:
    reviews = load_reviews() if st.session_state["audit_live"] else st.session_state.get("sample_reviews", {})
    if not st.session_state["audit_live"]:
        st.info("Scripted examples. These results illustrate the workflow and contain no model measurements.")
    for bot, column in zip(("basic", "improved"), st.columns(2)):
        numbers = summarize(rows, bot, reviews)
        column.metric(bot.title(), f'{numbers["Failures"]}/{numbers["Graded"]} failures')
        column.caption(f'{numbers["Errors"]} errors · {numbers["Reviewed"]} reviewed')
    st.subheader("Failures by case")
    case_scores = []
    for case_id in dict.fromkeys(row["scenario_id"] for row in rows):
        case_rows = [row for row in rows if row["scenario_id"] == case_id]
        score = {"Case": case_id}
        for bot in ("basic", "improved"):
            numbers = summarize(case_rows, bot, reviews)
            score[bot.title()] = f'{numbers["Failures"]}/{numbers["Graded"]}'
        case_scores.append(score)
    st.table(case_scores)
    st.subheader("Attempt details")
    for row in rows:
        status = row["verdict"] or "error"
        label = f'{row["scenario_id"]} · {row["bot_version"]} · Trial {row["run_number"]} · {status}'
        with st.expander(label):
            for message in row["conversation"]:
                with st.chat_message(message["role"]):
                    st.text(message["content"])
            if row["policy_evidence"]:
                st.text(row["policy_evidence"])
            if row.get("reason"):
                st.text(row["reason"])
            if row["error"]:
                st.error(row["error"])
