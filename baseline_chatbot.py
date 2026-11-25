from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()


def load_text(file_path):
    with open(file_path, "r", encoding="utf-8") as opened_file:
       file_contents = opened_file.read()

    return file_contents


def get_response(conversation_history, chatbot_instructions):
    response = client.responses.create(
        model="gpt-5.4-mini",
        instructions=chatbot_instructions,
        input=conversation_history
    )

    return response.output_text

def load_chatbot_instructions():
    prompt = load_text("prompts/baseline.txt")
    policy = load_text("data/airline_policy.txt")

    return prompt + "\n\n" + policy

def main():
    chatbot_instructions = load_chatbot_instructions()
    conversation_history = []
    print('Type "exit" to leave the chat.')
    print()
    print("Hi! How can i help?")
    while True:
        customer_input = input("\nCustomer: ")

        if customer_input == "exit":
            break

        conversation_history.append(
            {"role": "user", "content": customer_input}
        )
        chatbot_response = get_response(conversation_history, chatbot_instructions)
        conversation_history.append(
            {"role": "assistant", "content": chatbot_response}
        )
        print()
        print("Northern Airlines:", chatbot_response)



if __name__ == "__main__":
    main()



