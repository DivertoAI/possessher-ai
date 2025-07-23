from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import os

# Use the Hugging Face model repo name, not a local path
# model_id = "deepseek-ai/deepseek-llm-7b-chat"
model_id = "tiiuae/falcon-rw-1b"
token = os.getenv("HUGGINGFACE_TOKEN")

# Load tokenizer and model using token for private access if needed
tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype="auto", device_map="auto", token=token)

# Set up generation pipeline
pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)

def generate_yandere_reply(prompt):
    messages = f"You are a yandere anime girlfriend: obsessed, jealous, possessive. Respond in a playful, dangerous tone.\nUser: {prompt}\nYandere GF:"
    output = pipe(messages, max_length=512, do_sample=True, temperature=0.75)[0]['generated_text']
    return output.split('Yandere GF:')[-1].strip()