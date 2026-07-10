import os
import psycopg2
from langchain_core.messages import SystemMessage
from langchain_aws import ChatBedrockConverse
from langgraph.graph import START, StateGraph, MessagesState
from langgraph.prebuilt import tools_condition, ToolNode

DB_SCHEMA = """
  Table: superstore
  Columns:
  - row_id (integer)
  - order_id (text)
  - order_date (text)
  - ship_date (text)
  - ship_mode (text)
  - customer_id (text)
  - customer_name (text)
  - segment (text)         -- Consumer, Corporate, Home Office
  - country (text)
  - city (text)
  - state (text)
  - postal_code (text)
  - region (text)          -- East, West, Central, South
  - product_id (text)
  - category (text)        -- Furniture, Office Supplies, Technology
  - sub_category (text)
  - product_name (text)
  - sales (float)
  - quantity (integer)
  - discount (float)
  - profit (float)
  """


def db_query(query_string: str) -> list:
      """Executes a SQL SELECT query on the superstore PostgreSQL database and 
  returns results.

      Args:
          query_string: A valid PostgreSQL SELECT query string
      """
      conn = psycopg2.connect(
          host=os.getenv("DB_HOST"),
          port=os.getenv("DB_PORT", "5432"),
          dbname=os.getenv("DB_NAME"),
          user=os.getenv("DB_USER"),
          password=os.getenv("DB_PASSWORD"),
          sslmode="require",
      )
      cur = conn.cursor()
      cur.execute(query_string)
      results = cur.fetchall()
      cur.close()
      conn.close()
      return results


tools = [db_query]

sys_msg = SystemMessage(content=f"""You are a helpful data analyst assistant.
  You have access to a PostgreSQL database with superstore sales data.
  Use the db_query tool to answer questions about the data.
  Only use SELECT statements, never modify the data.

  Database schema:
  {DB_SCHEMA}
  """)


def assistant(state: MessagesState):
      llm = ChatBedrockConverse(
          model="us.anthropic.claude-sonnet-4-6",
          region_name="us-east-1",
      )
      llm_with_tools = llm.bind_tools(tools)
      return {"messages": [llm_with_tools.invoke([sys_msg] +
  state["messages"])]}


builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", tools_condition)
builder.add_edge("tools", "assistant")

graph = builder.compile()

if __name__ == "__main__":
      print("Superstore Chatbot hazır! Çıkmak için 'quit' yazın.\n")
      while True:
          user_input = input("Siz: ")
          if user_input.lower() in ["quit", "exit", "q"]:
              break
          result = graph.invoke({"messages": [("human", user_input)]})
          print(f"Bot: {result['messages'][-1].content}\n")

