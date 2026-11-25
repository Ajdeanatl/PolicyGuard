# PolicyGuard
AI chatbot testing and policy compliance tool.

## Run the prototype

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Click **Run Audit** to try scripted examples. The examples exercise the UI and
scoring pipeline without API calls. To run live, set the server environment
variables `OPENAI_API_KEY` and `OPENAI_MODEL`, restart Streamlit, and select
**Use live model**. Both bots and the audit judge use the configured model.
Each selected case generates two chatbot calls and two judge calls per trial.

The baseline uses the full policy and Andrew's baseline prompt. The improved
bot retrieves policy sections using topic keywords and includes instructions
for handling ambiguity and avoiding unauthorized promises. Both are scored by
a separate policy judge after answering.

Naomi's review page can consume `st.session_state["audit_rows"]`. Each attempt
is identified by `(case_id, bot, trial)`. Set `reviewer_verdict` to `pass` or
`fail` to override its score while retaining the original `ai_verdict`. Runs and
review decisions currently live in the active Streamlit session.
