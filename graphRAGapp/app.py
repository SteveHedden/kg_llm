import streamlit as st
import uuid
from rdflib import Graph
import os
from openai import OpenAI
from config import WCD_URL, WCD_API_KEY, OPENAI_API_KEY
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env


from query_functions.rdf_queries import (
    download_rdf_file,
    query_rdf,
    get_concept_triples_for_term,
    get_all_narrower_concepts,
    sanitize_term
)
from query_functions.weaviate_queries import (
    initialize_weaviate_client,
    query_weaviate_articles,
    query_weaviate_terms
)
import ast

# --- Initialization ---
if "article_results" not in st.session_state:
    st.session_state.article_results = []
if "selected_terms" not in st.session_state:
    st.session_state.selected_terms = {}
if "expanded_terms" not in st.session_state:
    st.session_state.expanded_terms = {}
if "current_search_terms" not in st.session_state:
    st.session_state.current_search_terms = []  # Terms displayed from the latest MeSH search
if "search_session_id" not in st.session_state:
    st.session_state.search_session_id = 0
if "node_registry" not in st.session_state:
    st.session_state.node_registry = {}
if "node_data" not in st.session_state:
    st.session_state.node_data = {}
if "node_widget_ids" not in st.session_state:
    st.session_state.node_widget_ids = {}
if "node_counter" not in st.session_state:
    st.session_state.node_counter = 0

st.title("Graph RAG for Medicine")
st.subheader("Semantic Search and Retrieval-Augmented Generation for Medical Journal Articles")


tabs = st.tabs(["1. Search Articles", "2. Refine Terms", "3. Filter & Summarize"])
tab_search, tab_refine, tab_filter = tabs

# --- TAB 1: Search Articles ---
with tab_search:
    st.header("Search Articles (Vector Query)")
    query_text = st.text_input("Enter your vector search term (e.g., Mouth Neoplasms):", key="vector_search")

    if st.button("Search Articles", key="search_articles_btn"):
        try:
            client = initialize_weaviate_client()
            article_results = query_weaviate_articles(client, query_text)

            # Extract URIs here
            article_uris = [
                result["properties"].get("article_URI")
                for result in article_results
                if result["properties"].get("article_URI")
            ]

            # Store article_uris in the session state
            st.session_state.article_uris = article_uris

            st.session_state.article_results = [
                {
                    "Title": result["properties"].get("title", "N/A"),
                    "Abstract": (result["properties"].get("abstractText", "N/A")[:100] + "..."),
                    "Distance": result["distance"],
                    "MeSH Terms": ", ".join(
                        ast.literal_eval(result["properties"].get("meshMajor", "[]"))
                        if result["properties"].get("meshMajor") else []
                    ),
                }
                for result in article_results
            ]
            client.close()
        except Exception as e:
            st.error(f"Error during article search: {e}")

    if st.session_state.article_results:
        st.write("**Search Results for Articles:**")
        st.table(st.session_state.article_results)
    else:
        st.write("No articles found yet.")

def get_node_id(term, path):
    key = (term, tuple(path), st.session_state.search_session_id)
    if key not in st.session_state.node_registry:
        st.session_state.node_registry[key] = st.session_state.node_counter
        st.session_state.node_counter += 1
        #print(f"Assigned node_id {st.session_state.node_registry[key]} to key {key}")
    return st.session_state.node_registry[key]

# --- Helper Function for Recursive Display ---
def display_term(term, path=None, visited=None, level=0):
    if path is None:
        path = []
    if visited is None:
        visited = set()

    node_id = get_node_id(term, path)

    # If we've seen this term before to avoid loops:
    if node_id in visited:
        indent = "&emsp;" * (level * 4)
        st.markdown(f"{indent}_Already displayed {term}, skipping._", unsafe_allow_html=True)
        return
    visited.add(node_id)

    # Indent and prefix
    indent = "&emsp;" * (level * 4)
    prefix = "" if level == 0 else "└─ "

    # Create stable keys using node_id
    path_str = "_".join(path)
    term_key = f"cb_{node_id}"
    expand_button_key = f"expand_{node_id}"

    # Initialize selected_terms if needed
    if term not in st.session_state.selected_terms:
        st.session_state.selected_terms[term] = False

    # Checkbox for the term
    st.session_state.selected_terms[term] = st.checkbox(
        f"{indent}{prefix}{term}",
        value=st.session_state.selected_terms[term],
        key=term_key
    )

    # Ensure node_data exists for this node
    if node_id not in st.session_state.node_data:
        # Initially no data fetched
        st.session_state.node_data[node_id] = {
            "term": term,
            "alt_names": [],
            "narrower_concepts": {},
            "expanded": False
        }

    expanded = st.session_state.node_data[node_id]["expanded"]
    expand_label = "Collapse" if expanded else "Expand"

    if st.button(f"{indent}{prefix}{expand_label} {term}", key=expand_button_key):
        if expanded:
            # Collapse
            st.session_state.node_data[node_id]["expanded"] = False
        else:
            # Fetch and process data
            alt_names = get_concept_triples_for_term(term)
            narrower_concepts = get_all_narrower_concepts(term, depth=1)

            # Deduplicate alt_names
            alt_names = list(dict.fromkeys(alt_names))  # Another quick way to deduplicate

            # Deduplicate narrower concepts
            for n in narrower_concepts:
                narrower_concepts[n] = list(dict.fromkeys(narrower_concepts[n]))

            # Store processed data
            st.session_state.node_data[node_id]["alt_names"] = alt_names
            st.session_state.node_data[node_id]["narrower_concepts"] = narrower_concepts
            st.session_state.node_data[node_id]["expanded"] = True
            expanded = True

    # If expanded, show alt_names and narrower_concepts
    if expanded:
        alt_names = st.session_state.node_data[node_id]["alt_names"]
        narrower_concepts = st.session_state.node_data[node_id]["narrower_concepts"]

        # Show alt names
        if alt_names:
            st.markdown(f"{indent}**Alternative Names:**", unsafe_allow_html=True)
            for alt_name in alt_names:
                alt_path = path + [term, "alt"]
                alt_path_str = "_".join(alt_path)
                child_id = get_node_id(alt_name, alt_path)
                alt_key = f"alt_{child_id}"
                if alt_name not in st.session_state.selected_terms:
                    st.session_state.selected_terms[alt_name] = False
                st.session_state.selected_terms[alt_name] = st.checkbox(
                    f"{indent}&emsp;&emsp;• {alt_name}",
                    value=st.session_state.selected_terms[alt_name],
                    key=alt_key
                )

        # Show narrower concepts
        if narrower_concepts:
            st.markdown(f"{indent}**Narrower Concepts:**", unsafe_allow_html=True)
            for narrower, children in narrower_concepts.items():
                st.markdown(f"{indent}&emsp;• **{narrower}**", unsafe_allow_html=True)
                for child in children:
                    display_term(child, path=path+[term, narrower], visited=visited, level=level+1)

# --- TAB 2: Refine Terms ---
with tab_refine:
    st.header("Refine MeSH Terms for Filtering")
    mesh_query_text = st.text_input("Enter a MeSH term for refinement:", key="mesh_search_input")

    if st.button("Search MeSH Terms", key="search_mesh_terms_btn"):
        st.session_state.search_session_id += 1
        try:
            # Clear displayed terms and expansions
            st.session_state.current_search_terms.clear()
            st.session_state.node_registry = {}
            st.session_state.node_data = {}
            st.session_state.node_counter = 0

            client = initialize_weaviate_client()
            term_results = query_weaviate_terms(client, mesh_query_text)

            # Collect unique sanitized terms
            sanitized_terms = set()
            for result in term_results:
                sanitized_term = sanitize_term(result["properties"].get("meshTerm", "N/A"))
                sanitized_terms.add(sanitized_term)

            st.session_state.current_search_terms = list(sanitized_terms)

            # Initialize selected_terms if needed
            for term in st.session_state.current_search_terms:
                if term not in st.session_state.selected_terms:
                    st.session_state.selected_terms[term] = False

            client.close()
        except Exception as e:
            st.error(f"Error during term search: {e}")

    # Display only current search terms (fresh results)
    if st.session_state.current_search_terms:
        st.subheader("Current Search Results for MeSH Terms")
        st.write("Select terms and expand them to find alternative names and narrower concepts.")
        for term in st.session_state.current_search_terms:
            display_term(term, path=[term], visited=set(), level=0)
    else:
        st.write("No current search results. Enter a MeSH term and click 'Search MeSH Terms'.")

# SIDEBAR
with st.sidebar:
    st.header("Selected Terms")
    selected_display = [t for t, selected in st.session_state.selected_terms.items() if selected]
    if selected_display:
        st.write(", ".join(selected_display))
    else:
        st.write("No terms selected yet.")
    st.write("---")
    st.write("**Instructions:**")
    st.write("1. 'Search Articles' to find relevant articles.")
    st.write("2. 'Refine Terms' to find and select MeSH terms.")
    st.write("3. 'Filter & Summarize' to apply filters and get summaries.")

# --- TAB 3: Filter & Summarize ---
with tab_filter:
    st.header("Filter and Summarize Results")
    final_terms = [t for t, selected in st.session_state.selected_terms.items() if selected]
    LOCAL_FILE_PATH = "PubMedGraph.ttl"

    if final_terms:
        st.write("**Final Bucket of Terms for Filtering:**")
        st.write(", ".join(final_terms))

        # Download the RDF file if not already done
        if "rdf_file_downloaded" not in st.session_state:
            try:
                download_rdf_file(LOCAL_FILE_PATH, "PubMedGraph.ttl")
                st.session_state.rdf_file_downloaded = True
            except Exception as e:
                st.error(f"Error downloading RDF file: {e}")

        if st.button("Filter Articles"):
            try:
                # Check if we have URIs from tab 1
                if "article_uris" in st.session_state and st.session_state.article_uris:
                    article_uris = st.session_state.article_uris

                    # Convert list of URIs into a string for the VALUES clause or FILTER
                    article_uris_string = ", ".join([f"<{str(uri)}>" for uri in article_uris])

                    SPARQL_QUERY = """
                    PREFIX schema: <http://schema.org/>
                    PREFIX ex: <http://example.org/>

                    SELECT ?article ?title ?abstract ?datePublished ?access ?meshTerm
                    WHERE {{
                      ?article a ex:Article ;
                               schema:name ?title ;
                               schema:description ?abstract ;
                               schema:datePublished ?datePublished ;
                               ex:access ?access ;
                               schema:about ?meshTerm .

                      ?meshTerm a ex:MeSHTerm .

                      FILTER (?article IN ({article_uris}))
                    }}
                    """
                    # Insert the article URIs into the query
                    query = SPARQL_QUERY.format(article_uris=article_uris_string)
                else:
                    st.write("No articles selected from Tab 1.")
                    st.stop()

                # Query the RDF and save results in session state
                top_articles = query_rdf(LOCAL_FILE_PATH, query, final_terms)
                st.session_state.filtered_articles = top_articles

                if top_articles:
                    # Combine abstracts from top articles and save in session state
                    def combine_abstracts(ranked_articles):
                        combined_text = " ".join(
                            [f"Title: {data['title']} Abstract: {data['abstract']}" for article_uri, data in
                             ranked_articles]
                        )
                        return combined_text

                    st.session_state.combined_text = combine_abstracts(top_articles)

                else:
                    st.write("No articles found for the selected terms.")
            except Exception as e:
                st.error(f"Error filtering articles: {e}")

        # Summarize with LLM button
        if "user_query" not in st.session_state:
            st.session_state.user_query = "Summarize the key information here in bullet points. Make it understandable to someone without a medical degree."

        # Update the user query directly from the text area
        st.session_state.user_query = st.text_area(
            "Enter your query for the LLM:",
            value=st.session_state.user_query,
            key="user_query_text_area",
            height=100,
        )

        # Display the original articles first
        if "filtered_articles" in st.session_state and st.session_state.filtered_articles:
            st.subheader("Original Articles")
            for article_uri, data in st.session_state.filtered_articles:
                st.write(f"**Title:** {data['title']}")
                st.write(f"**Abstract:** {data['abstract']}")
                st.write("**MeSH Terms:**")
                for mesh_term in data['meshTerms']:
                    st.write(f"- {mesh_term}")
                st.write("---")

        # Summarize with LLM button
        if st.button("Summarize with LLM"):
            try:
                if "combined_text" in st.session_state and st.session_state["combined_text"].strip():
                    combined_text = st.session_state["combined_text"]
                    user_query = st.session_state.user_query


                    # Function to generate summary
                    def generate_summary(combined_text, user_query):
                        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

                        GPT_MODELS = ["gpt-4o", "gpt-4o-mini"]
                        response = client.chat.completions.create(
                            messages=[
                                {'role': 'system', 'content': 'You summarize medical texts.'},
                                {'role': 'user', 'content': f"{user_query}\n\n{combined_text}"},
                            ],
                            model=GPT_MODELS[1],
                            temperature=0,
                        )

                        # Extract the summary from the assistant's response
                        summary = response.choices[0].message.content.strip()
                        return summary


                    # Generate and display the summary
                    with st.spinner("Generating summary..."):
                        summary = generate_summary(combined_text, user_query)
                    st.subheader("Summary")
                    st.write(summary)
                else:
                    st.error("No combined text available for summarization. Please filter articles first.")
            except Exception as e:
                st.error(f"Error summarizing articles: {e}")


