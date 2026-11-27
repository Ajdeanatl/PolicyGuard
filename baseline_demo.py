from baseline_chatbot import get_response, load_chatbot_instructions
import streamlit as st

st.title("Northern Airlines")
st.caption("Customer Support")

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if st.button("New conversation"):
    st.session_state.conversation_history = []

customer_input = st.chat_input("How can I help you?")

if customer_input:
    st.session_state.conversation_history.append(
        {"role": "user", "content": customer_input}
    )

    chatbot_instructions = load_chatbot_instructions()

    chatbot_response = get_response(
        st.session_state.conversation_history,
        chatbot_instructions
    )

    st.session_state.conversation_history.append(
        {"role": "assistant", "content": chatbot_response}
    )

for message in st.session_state.conversation_history:
    with st.chat_message(message["role"]):
        st.write(message["content"])