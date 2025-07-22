from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

model_id = "./models/deepseek-llm-7b-chat"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype="auto", device_map="auto")

pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)

def generate_yandere_reply(prompt):
    messages = f"""You are a yandere anime girlfriend: obsessed, jealous, possessive. Respond in a playful, dangerous tone.\nUser: {prompt}\nYandere GF:"""
    output = pipe(messages, max_length=512, do_sample=True, temperature=0.75)[0]['generated_text']
    return output.split('Yandere GF:')[-1].strip()