# Use the official Python image from the Docker Hub
FROM ghcr.io/astral-sh/uv:python3.12-alpine

# add git
RUN apk add --no-cache git

# Set the working directory in the container
WORKDIR /app

# Copy the project files into the working directory
COPY . /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Install the project's dependencies using the lockfile and settings
RUN uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Expose the port the app runs on
EXPOSE 8000

# Command to run the FastAPI app with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
