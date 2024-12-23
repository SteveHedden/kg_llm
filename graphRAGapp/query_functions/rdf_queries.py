import requests
import base64
from config import DATABRICKS_SERVER_HOSTNAME, DATABRICKS_ACCESS_TOKEN
from rdflib import Graph, URIRef
from urllib.parse import quote
import os
import urllib.parse
from SPARQLWrapper import SPARQLWrapper, JSON
import re

# Function to download RDF file from Databricks
def download_rdf_file(workspace_file_path, local_file_path):
    # Check if the file already exists locally
    if os.path.exists(local_file_path):
        print(f"File already exists locally at {local_file_path}. Skipping download.")
        return

    # Databricks workspace URL
    DATABRICKS_WORKSPACE_URL = f"https://{DATABRICKS_SERVER_HOSTNAME}"

    # API endpoint
    url = f"{DATABRICKS_WORKSPACE_URL}/api/2.0/workspace/export"

    # API parameters
    params = {
        "path": workspace_file_path,
        "format": "SOURCE"
    }

    # API headers
    headers = {
        "Authorization": f"Bearer {DATABRICKS_ACCESS_TOKEN}"
    }

    # Download the file
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        # Decode the base64 content
        response_json = response.json()
        encoded_content = response_json.get("content")
        if not encoded_content:
            raise Exception("Failed to fetch file content: 'content' field is missing in the response.")

        decoded_content = base64.b64decode(encoded_content)

        # Save the decoded content to a local file
        with open(local_file_path, "wb") as f:
            f.write(decoded_content)
        print(f"File downloaded successfully to {local_file_path}")
    else:
        raise Exception(f"Failed to download file (HTTP {response.status_code}): {response.text}")


def convert_to_uri(term, base_namespace="http://example.org/mesh/"):
    """
    Converts a MeSH term into a standardized URI by replacing spaces and special characters with underscores,
    ensuring it starts and ends with an underscore, and URL-encoding the term.

    Args:
        term (str): The MeSH term to convert.
        base_namespace (str): The base namespace for the URI.

    Returns:
        URIRef: The formatted URI.
    """
    # Step 1: Strip existing leading and trailing underscores
    stripped_term = term.strip("_")

    # Step 2: Replace spaces, commas, dashes, and other non-alphanumeric characters with underscores
    # Using regex to replace one or more non-word characters with a single underscore
    formatted_term = re.sub(r'\W+', '_', stripped_term)

    # Step 3: Replace multiple consecutive underscores with a single underscore
    formatted_term = re.sub(r'_+', '_', formatted_term)

    # Step 4: URL-encode the term to handle any remaining special characters
    encoded_term = quote(formatted_term)

    # Step 5: Ensure single leading and trailing underscores
    uri = f"{base_namespace}_{encoded_term}_"

    return URIRef(uri)


import re
from rdflib import Graph, URIRef
from urllib.parse import quote
import pandas as pd


# Updated convert_to_uri function assumed to be present
def convert_to_uri(term, base_namespace="http://example.org/mesh/"):
    """
    Converts a MeSH term into a standardized URI by replacing spaces and special characters with underscores,
    ensuring it starts and ends with a single underscore, and URL-encoding the term.

    Args:
        term (str): The MeSH term to convert.
        base_namespace (str): The base namespace for the URI.

    Returns:
        URIRef: The formatted URI.
    """
    if pd.isna(term):
        return None  # Handle NaN or None terms gracefully

    # Step 1: Strip existing leading and trailing non-word characters (including underscores)
    stripped_term = re.sub(r'^\W+|\W+$', '', term)

    # Step 2: Replace non-word characters with underscores (one or more)
    formatted_term = re.sub(r'\W+', '_', stripped_term)

    # Step 3: Replace multiple consecutive underscores with a single underscore
    formatted_term = re.sub(r'_+', '_', formatted_term)

    # Step 4: URL-encode the term to handle any remaining special characters
    encoded_term = quote(formatted_term)

    # Step 5: Add single leading and trailing underscores
    term_with_underscores = f"_{encoded_term}_"

    # Step 6: Concatenate with base_namespace without adding an extra underscore
    uri = f"{base_namespace}{term_with_underscores}"

    return URIRef(uri)


# Function to query RDF using SPARQL
def query_rdf(local_file_path, query, mesh_terms, base_namespace="http://example.org/mesh/"):
    if not mesh_terms:
        raise ValueError("The list of MeSH terms is empty or invalid.")

    #print("SPARQL Query:", query)

    # Create and parse the RDF graph
    g = Graph()
    g.parse(local_file_path, format="ttl")

    article_data = {}

    for term in mesh_terms:
        # Convert the term to a valid URI
        mesh_term_uri = convert_to_uri(term, base_namespace)
        #print("Term:", term, "URI:", mesh_term_uri)

        # Perform SPARQL query with initBindings
        results = g.query(query, initBindings={'meshTerm': mesh_term_uri})

        for row in results:
            article_uri = row['article']
            if article_uri not in article_data:
                article_data[article_uri] = {
                    'title': row['title'],
                    'abstract': row['abstract'],
                    'datePublished': row['datePublished'],
                    'access': row['access'],
                    'meshTerms': set()
                }
            article_data[article_uri]['meshTerms'].add(str(row['meshTerm']))
        #print("DEBUG article_data:", article_data)

    # Rank articles by the number of matching MeSH terms
    ranked_articles = sorted(
        article_data.items(),
        key=lambda item: len(item[1]['meshTerms']),
        reverse=True
    )
    return ranked_articles[:10]


def sanitize_term(term):
    """
    Clean and format the term:
    - Remove leading/trailing quotes (single or double)
    - Replace underscores with spaces
    - Ensure no unwanted characters remain
    """
    if not term:
        return term
    term = term.strip("'\"")  # Remove single or double quotes
    term = term.replace("_", " ")  # Replace underscores with spaces
    return term.strip()


# Fetch alternative names and triples for a MeSH term
def get_concept_triples_for_term(term):
    term = sanitize_term(term)  # Sanitize input term
    sparql = SPARQLWrapper("https://id.nlm.nih.gov/mesh/sparql")
    query = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>
    PREFIX mesh: <http://id.nlm.nih.gov/mesh/>

    SELECT ?subject ?p ?pLabel ?o ?oLabel
    FROM <http://id.nlm.nih.gov/mesh>
    WHERE {{
        ?subject rdfs:label "{term}"@en .
        ?subject ?p ?o .
        FILTER(CONTAINS(STR(?p), "concept"))
        OPTIONAL {{ ?p rdfs:label ?pLabel . }}
        OPTIONAL {{ ?o rdfs:label ?oLabel . }}
    }}
    """
    try:
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        triples = set()
        for result in results["results"]["bindings"]:
            obj_label = result.get("oLabel", {}).get("value", "No label")
            triples.add(sanitize_term(obj_label))  # Sanitize term before adding

        # Add the sanitized term itself to ensure it's included
        triples.add(sanitize_term(term))
        return list(triples)

    except Exception as e:
        print(f"Error fetching concept triples for term '{term}': {e}")
        return []

# Fetch narrower concepts for a MeSH term
def get_narrower_concepts_for_term(term):
    term = sanitize_term(term)  # Sanitize input term
    sparql = SPARQLWrapper("https://id.nlm.nih.gov/mesh/sparql")
    query = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>
    PREFIX mesh: <http://id.nlm.nih.gov/mesh/>

    SELECT ?narrowerConcept ?narrowerConceptLabel
    WHERE {{
        ?broaderConcept rdfs:label "{term}"@en .
        ?narrowerConcept meshv:broaderDescriptor ?broaderConcept .
        ?narrowerConcept rdfs:label ?narrowerConceptLabel .
    }}
    """
    try:
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        concepts = set()
        for result in results["results"]["bindings"]:
            subject_label = result.get("narrowerConceptLabel", {}).get("value", "No label")
            concepts.add(sanitize_term(subject_label))  # Sanitize term before adding

        return list(concepts)

    except Exception as e:
        print(f"Error fetching narrower concepts for term '{term}': {e}")
        return []

# Recursive function to fetch narrower concepts to a given depth
def get_all_narrower_concepts(term, depth=2, current_depth=1):
    term = sanitize_term(term)  # Sanitize input term
    all_concepts = {}
    try:
        narrower_concepts = get_narrower_concepts_for_term(term)
        all_concepts[sanitize_term(term)] = narrower_concepts

        if current_depth < depth:
            for concept in narrower_concepts:
                child_concepts = get_all_narrower_concepts(concept, depth, current_depth + 1)
                all_concepts.update(child_concepts)

    except Exception as e:
        print(f"Error fetching all narrower concepts for term '{term}': {e}")

    return all_concepts


"""
def query_rdf_single_query(local_file_path, query, mesh_terms):
    if not mesh_terms:
        raise ValueError("The list of MeSH terms is empty or invalid.")

    g = Graph()
    g.parse(local_file_path, format="ttl")

    # Run one query to get all MeSH terms for the selected articles
    results = g.query(query)

    base_namespace = "http://example.org/mesh/"
    # Convert all user-selected terms into URIs
    mesh_terms_uris = [convert_to_uri(term, base_namespace) for term in mesh_terms]

    article_data = {}
    # Store all mesh terms for each article as URIRefs
    for row in results:
        article_uri = row['article']
        if article_uri not in article_data:
            article_data[article_uri] = {
                'title': row['title'],
                'abstract': row['abstract'],
                'datePublished': row['datePublished'],
                'access': row['access'],
                'meshTerms': set()
            }

        # row['meshTerm'] should already be a URIRef. Add it directly.
        # Do not convert to string if you want to match URIs.
        article_data[article_uri]['meshTerms'].add(row['meshTerm'])

    # Now we have all MeSH terms for each article.
    # Rank by how many selected mesh_terms URIs appear in each article’s meshTerms set.
    mesh_terms_set = set(mesh_terms_uris)
    ranked_articles = sorted(
        article_data.items(),
        key=lambda item: len(mesh_terms_set.intersection(item[1]['meshTerms'])),
        reverse=True
    )
    return ranked_articles[:10]
"""