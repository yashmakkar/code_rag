from fastmcp import FastMCP
import json




mcp = FastMCP("CodeRAG Server")

@mcp.custom_route("/health", methods=["GET"])
def health_probe():
    return json.dumps(
        {"status": "healthy"}
    )

@mcp.tool
def greet(name: str) -> str:
    """Greets a person with the given name."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="http")
