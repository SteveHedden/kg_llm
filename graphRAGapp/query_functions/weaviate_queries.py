import weaviate
from weaviate import Client as WeaviateClient
from config import WCD_URL, WCD_API_KEY, OPENAI_API_KEY
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery

# Initialize Weaviate Client
def initialize_weaviate_client():
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=WCD_URL,
        auth_credentials=Auth.api_key(WCD_API_KEY),
        headers={'X-OpenAI-Api-key': OPENAI_API_KEY}
    )
    return client

# Function to query Weaviate for Articles
def query_weaviate_articles(client, query_text, limit=10):
    # Perform vector search on Article collection
    response = client.collections.get("Article").query.near_text(
        query=query_text,
        limit=limit,
        return_metadata=MetadataQuery(distance=True)
    )

    # Parse response
    results = []
    for obj in response.objects:
        results.append({
            "uuid": obj.uuid,
            "properties": obj.properties,
            "distance": obj.metadata.distance,
        })
    return results

# Function to query Weaviate for MeSH Terms
def query_weaviate_terms(client, query_text, limit=10):
    # Perform vector search on MeshTerm collection
    response = client.collections.get("term").query.near_text(
        query=query_text,
        limit=limit,
        return_metadata=MetadataQuery(distance=True)
    )

    # Parse response
    results = []
    for obj in response.objects:
        results.append({
            "uuid": obj.uuid,
            "properties": obj.properties,
            "distance": obj.metadata.distance,
        })
    return results
