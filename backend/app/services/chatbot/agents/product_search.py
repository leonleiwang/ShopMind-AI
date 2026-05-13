from app.services.chatbot.tools.caller import ToolCaller


class ProductSearchAgent:
    """Agent wrapper for product discovery.

    ChatService keeps the streaming orchestration, while this agent provides a
    reusable unit for tests, MCP adapters, or future graph-based orchestration.
    """

    async def search(self, params: dict) -> dict:
        products = await ToolCaller.invoke("search_products", **params)
        if not products:
            return {"products": [], "text": "没有找到符合条件的商品，试试换个关键词吧～"}
        product_lines = "\n".join(
            [f"- 商品{product['id']}：{product['name']} (¥{product['price']})" for product in products[:5]]
        )
        return {"products": products, "text": f"为你找到以下商品：\n{product_lines}"}
