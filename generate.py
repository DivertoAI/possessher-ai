from diffusers import StableDiffusionPipeline
import torch
from datetime import datetime
import os
import glob

# Constants
model_repo = "gsdf/Counterfeit-V2.5"
local_model_path = "/workspace/models/Counterfeit-V2.5"
output_dir = "./outputs/generated"

# Detect if model is already downloaded as a snapshot
snapshot_dirs = glob.glob(os.path.join(local_model_path, "models--gsdf--Counterfeit-V2.5", "snapshots", "*"))

# Load the model
if snapshot_dirs:
    actual_model_path = snapshot_dirs[0]
    pipe = StableDiffusionPipeline.from_pretrained(
        actual_model_path,
        torch_dtype=torch.float16,
        safety_checker=None  # 🚫 Disable safety filters
    )
else:
    pipe = StableDiffusionPipeline.from_pretrained(
        model_repo,
        cache_dir=local_model_path,
        torch_dtype=torch.float16,
        safety_checker=None  # 🚫 Disable safety filters
    )

# Move pipeline to GPU
pipe.to("cuda")

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# 🧠 Persona Prompt: Upgraded for appeal and consistency
BASE_PROMPT = (
    "masterpiece, best quality, yandere anime waifu, consistent face, intense eyes, "
    "seductive expression, beautiful detailed face, long hair, soft lighting, blush, "
    "bare shoulders, slim waist, big boobs, beautiful big butt, nude, nsfw"
)

# 🚫 Negative prompt to reduce artifacts and censorship
NEGATIVE_PROMPT = (
    "clothes, bra, shirt, pants, censorship, watermark, blurry, bad anatomy, extra limbs, "
    "poorly drawn, deformed, out of frame, cropped, text"
)

# 🔥 Image Generation Function
def generate_image(user_id, user_prompt=None):
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"{user_id}_{timestamp}.png"
    full_path = os.path.join(output_dir, filename)

    prompt = BASE_PROMPT
    if user_prompt:
        prompt += f", {user_prompt}"

    try:
        image = pipe(
            prompt=prompt,
            negative_prompt=NEGATIVE_PROMPT,
            guidance_scale=7.5
        ).images[0]

        image.save(full_path)
        return full_path
    except Exception as e:
        print(f"[ERROR] Image generation failed: {e}")
        return None