# Product Search Agent：封装商品发现能力，供 ChatService、测试和未来图编排复用。
from app.services.chatbot.tools.caller import ToolCaller


class ProductSearchAgent:
    """Agent wrapper for product discovery.

    ChatService keeps the streaming orchestration, while this agent provides a
    reusable unit for tests, MCP adapters, or future graph-based orchestration.
    """

    def __init__(self, tool_caller: ToolCaller):
        # 通过统一 ToolCaller 调用 search_products 工具。
        self.tool_caller = tool_caller

    async def search(self, params: dict) -> dict:
        # 执行商品搜索并把结果转为结构化 products + 用户可读文本。
        products = await self.tool_caller.invoke("search_products", **params)
        if not products:
            return {"products": [], "text": "没有找到符合条件的商品，试试换个关键词吧～"}
        product_lines = "\n".join(
            [f"- 商品{product['id']}：{product['name']} (¥{product['price']})" for product in products[:5]]
        )
        return {"products": products, "text": f"为你找到以下商品：\n{product_lines}"}
