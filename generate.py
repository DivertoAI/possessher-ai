from diffusers import StableDiffusionPipeline
import torch
from datetime import datetime
import os

# Constants
model_repo = "gsdf/Counterfeit-V2.5"
local_model_path = "/workspace/models/Counterfeit-V2.5"
output_dir = "./outputs/generated"

# Download model if not cached locally
if not os.path.isdir(local_model_path) or not os.listdir(local_model_path):
    pipe = StableDiffusionPipeline.from_pretrained(
        model_repo,
        cache_dir=local_model_path,
        torch_dtype=torch.float16
    )
else:
    pipe = StableDiffusionPipeline.from_pretrained(
        local_model_path,
        torch_dtype=torch.float16
    )

# Move to GPU
pipe.to("cuda")

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

def generate_image(user_id, prompt):
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"{user_id}_{timestamp}.png"
    full_path = os.path.join(output_dir, filename)

    try:
        image = pipe(prompt, guidance_scale=7.5).images[0]
        image.save(full_path)
        return full_path
    except Exception as e:
        print(f"[ERROR] Image generation failed: {e}")
        return None