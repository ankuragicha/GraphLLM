import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from dotenv import load_dotenv
load_dotenv()

from langchain_community.graphs import Neo4jGraph
from langchain_groq import ChatGroq
 
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document

os.environ["NEO4J_URI"]=os.getenv("NEO4J_URI")
os.environ["NEO4J_USERNAME"]=os.getenv("NEO4J_USERNAME")
os.environ["NEO4J_PASSWORD"]=os.getenv("NEO4J_PASSWORD")
os.environ["Groq_api_key"] = os.getenv("GROQ_API_KEY")
llm=ChatGroq(groq_api_key=Groq_api_key,model_name="Gemma-9b-it")

from neo4j import GraphDatabase
driver = GraphDatabase.driver(uri=NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def connect_to_neo():
    graph=Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USERNAME,
    password=NEO4J_PASSWORD,
    )

def get_pdf_text(pdf_docs):
    text=""
    for pdf in pdf_docs:
        pdf_reader= PdfReader(pdf)
        for page in pdf_reader.pages:
            text+= page.extract_text()
    return  text

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_text(text)
    return chunks

def create_node(tx, node_id, node_type):
    query = f"CREATE (n:{node_type} {{ id: $id }})"
    tx.run(query, id=node_id)

def create_relationship(tx, source_id, relationship_type, target_id):
    query = (
        f"MATCH (a {{id: $source_id}}), (b {{id: $target_id}}) "
        f"CREATE (a)-[r:{relationship_type}]->(b) "
        "RETURN type(r)"
    )
    tx.run(query, source_id=source_id, target_id=target_id)

def load_graph_documents_to_neo4j(graph_documents):
    with driver.session() as session:
        for node in graph_documents[0].nodes:
            session.execute_write(create_node, node.id, node.type)
 
        for relationship in graph_documents[0].relationships:
            session.execute_write(create_relationship, relationship.source.id, relationship.type, relationship.target.id)



def main():
    st.set_page_config("Chat PDF")
    st.header("Chat with PDF using KnowledgeGraph💁")

    user_question = st.text_input("Ask a Question from the PDF Files")

    if user_question:
        user_input(user_question)

    with st.sidebar:
        st.title("Menu:")
        pdf_docs = st.file_uploader("Upload your PDF Files and Click on the Submit & Process Button", accept_multiple_files=True)
        if st.button("Submit & Process"):
            with st.spinner("Processing..."):
                raw_text = get_pdf_text(pdf_docs)
                text_chunks = get_text_chunks(raw_text)
                connect_to_neo()
                documents=[Document(page_content=text_chunks)]
                llm_transformer=LLMGraphTransformer(llm=llm)
                graph_documents=llm_transformer.convert_to_graph_documents(documents)
                load_graph_documents_to_neo4j(graph_documents)
                driver.close()
                st.success("Done")

if __name__ == "__main__":
    main()