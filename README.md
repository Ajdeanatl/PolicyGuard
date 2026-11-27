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

The baseline uses the full policy and Andrew's baseline prompt. The improved
bot retrieves policy sections using topic keywords and includes instructions
for handling ambiguity and avoiding unauthorized promises. Both are scored by
a separate policy judge after answering.

Each trial uses two chatbot turns and one judge call per bot. The judge
grades the conversation using the six verdicts from the test design.
On a live run, the app writes the latest results to `data/results.json`.
The Review page can also read the current session's results. Scripted runs
and their review decisions stay in session state. Live review decisions are
saved in `data/reviews.json`, and the scorecard uses corrections when available.

For a public scripted demo, deploy `app.py` without API credentials. Open the
app, run an audit, and open Review. For a local live check, select
`basic-24-hour`, use one trial, and verify both four-message conversations.

`api_cost` estimates USD for the two chatbot replies per bot and trial using
reported token usage and GPT-5 mini standard rates, including cached input
discounts and billed output tokens. Judge calls are excluded. Scripted rows,
unsupported models and incomplete reply measurements have a blank cost.
