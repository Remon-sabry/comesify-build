import runpod
from worker import handler

runpod.serverless.start({"handler": handler})
