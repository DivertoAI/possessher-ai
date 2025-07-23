from diffusers import StableDiffusionPipeline
import torch
from datetime import datetime
import os

# Path to the Hassaku Hentai model
model_id = "./models/hentai-diffusion-checkpoint"

# Load the pipeline once at module level (efficient)
pipe = StableDiffusionPipeline.from_pretrained(
    model_id,
    torch_dtype=torch.float16
).to("cuda")

def generate_image(user_id, prompt):
    # Ensure output directory exists
    output_dir = "./outputs/generated"
    os.makedirs(output_dir, exist_ok=True)

    # Create filename with UTC timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"{user_id}_{timestamp}.png"
    full_path = os.path.join(output_dir, filename)

    # Generate and save image
    image = pipe(prompt, guidance_scale=7.5).images[0]
    image.save(full_path)

    return full_path