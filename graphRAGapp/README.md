This is the code needed to build a Graph RAG app. The article describing the app in detail and the accompanying code is here: 

Here are the steps to get this running locally:

1. Clone this repo.
2. Create a .env file with the following values initialized:

`WCD_URL = <paste your Weaviate instance>`

`WCD_API_KEY = <paste your Weaviate API key>`

`OPENAI_API_KEY = <paste your OPENAI API key>`

3. Download this data: [PubMed MultiLabel Text Classification Dataset MeSH](https://www.kaggle.com/datasets/owaiskhan9654/pubmed-multilabel-text-classification)
4. Run the code in the notebook here titled, "VectorVsKG_updated.ipynb". I ran this from Databricks so you may need to adjust a few things.
5. Put the output file from that notebook (PubMedGraph.ttl) in the code folder with this app.
6. Install required dependencies.
7. Run the streamlit app:
   
   `streamlit run app.py`
