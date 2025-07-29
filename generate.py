from diffusers import StableDiffusionPipeline
import torch
from datetime import datetime
import os
import glob

# Constants
MODEL_REPO = "gsdf/Counterfeit-V2.5"
LOCAL_MODEL_PATH = "/workspace/models/Counterfeit-V2.5"
OUTPUT_DIR = "./outputs/generated"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Try to find existing snapshot if already downloaded
snapshot_dirs = glob.glob(os.path.join(
    LOCAL_MODEL_PATH, "models--gsdf--Counterfeit-V2.5", "snapshots", "*"
))

if snapshot_dirs:
    model_path = snapshot_dirs[0]
    print(f"[INFO] Using local model snapshot: {model_path}")
    pipe = StableDiffusionPipeline.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
        safety_checker=None
    )
else:
    print("[INFO] Downloading model from Hugging Face hub...")
    pipe = StableDiffusionPipeline.from_pretrained(
        MODEL_REPO,
        cache_dir=LOCAL_MODEL_PATH,
        torch_dtype=torch.float16,
        safety_checker=None
    )

# Move pipeline to GPU
pipe.to("cuda")

# Core Prompt
BASE_PROMPT = (
    "masterpiece, best quality, yandere anime waifu, consistent face, intense eyes, "
    "seductive expression, beautiful detailed face, long hair, soft lighting, blush, "
    "bare shoulders, slim waist, large boobs, beautiful large butt, nude, nsfw"
)

NEGATIVE_PROMPT = (
    "clothes, bra, shirt, pants, censorship, watermark, blurry, bad anatomy, extra limbs, "
    "poorly drawn, deformed, out of frame, cropped, text"
)

# Generate Image
def generate_image(user_id, user_prompt=None):
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"{user_id}_{timestamp}.png"
    full_path = os.path.join(OUTPUT_DIR, filename)

    full_prompt = f"{BASE_PROMPT}, {user_prompt}" if user_prompt else BASE_PROMPT

    try:
        result = pipe(
            prompt=full_prompt,
            negative_prompt=NEGATIVE_PROMPT,
            guidance_scale=7.5
        )
        result.images[0].save(full_path)
        print(f"[SUCCESS] Image saved to {full_path}")
        return full_path
    except Exception as e:
        print(f"[ERROR] Image generation failed: {e}")
        return None