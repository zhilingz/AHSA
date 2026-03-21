import os
import time
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL", "https://ie-crs.haoxiang.ai/v1"),
    api_key=os.getenv("OPENAI_API_KEY", ""),
)


def call_llm_api(prompt_text, model_name):
    completion = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt_text}],
        temperature=0,
    )
    return completion.choices[0].message.content


if __name__ == "__main__":
    prompt = "What model are you?"
    model = os.getenv("SKILL_CLUSTERING_MODEL", "google/gemini-3.1-flash-lite-preview")
    start_time = time.time()
    response = call_llm_api(prompt, model)
    elapsed = time.time() - start_time
    print(response)
    print(f"elapsed: {elapsed:.2f}s")
