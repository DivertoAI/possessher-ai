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

if snapshot_dirs:
    actual_model_path = snapshot_dirs[0]
    pipe = StableDiffusionPipeline.from_pretrained(
        actual_model_path,
        torch_dtype=torch.float16
    )
else:
    pipe = StableDiffusionPipeline.from_pretrained(
        model_repo,
        cache_dir=local_model_path,
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